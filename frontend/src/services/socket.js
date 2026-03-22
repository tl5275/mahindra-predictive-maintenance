import { buildFleetWebSocketUrl } from "./config";

const DEFAULT_OPTIONS = {
  initialReconnectDelayMs: 1000,
  maxReconnectDelayMs: 30000,
  maxReconnectAttempts: 10,
  backoffMultiplier: 2,
  reconnectJitterMs: 250,
  heartbeatIntervalMs: 20000,
  heartbeatTimeoutMs: 10000,
};

function normalizeSocketError(error) {
  if (error instanceof Error) {
    return error;
  }
  return new Error("WebSocket connection error.");
}

function safeParseMessage(data) {
  if (typeof data !== "string") {
    throw new Error("Unsupported WebSocket message type.");
  }

  const payload = JSON.parse(data);
  if (payload == null || typeof payload !== "object") {
    throw new Error("Unexpected WebSocket payload.");
  }

  return payload;
}

export function connectFleetSocket(callbacks = {}, options = {}) {
  const settings = { ...DEFAULT_OPTIONS, ...options };
  let socket = null;
  let reconnectTimer = null;
  let heartbeatTimer = null;
  let heartbeatTimeoutTimer = null;
  let reconnectAttempts = 0;
  let hasConnected = false;
  let disposed = false;
  let state = "idle";

  const clearReconnectTimer = () => {
    if (reconnectTimer !== null) {
      window.clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
  };

  const clearHeartbeat = () => {
    if (heartbeatTimer !== null) {
      window.clearInterval(heartbeatTimer);
      heartbeatTimer = null;
    }
    if (heartbeatTimeoutTimer !== null) {
      window.clearTimeout(heartbeatTimeoutTimer);
      heartbeatTimeoutTimer = null;
    }
  };

  const setState = (nextState, extra = {}) => {
    state = nextState;
    callbacks.onStateChange?.({
      status: nextState,
      retryCount: reconnectAttempts,
      ...extra,
    });
  };

  const detachSocket = ({ close = false, code = 1000, reason = "Closing socket" } = {}) => {
    const currentSocket = socket;
    socket = null;

    if (!currentSocket) {
      return;
    }

    currentSocket.onopen = null;
    currentSocket.onclose = null;
    currentSocket.onerror = null;
    currentSocket.onmessage = null;

    if (
      close &&
      (currentSocket.readyState === WebSocket.OPEN || currentSocket.readyState === WebSocket.CONNECTING)
    ) {
      currentSocket.close(code, reason);
    }
  };

  const scheduleHeartbeatTimeout = () => {
    if (heartbeatTimeoutTimer !== null) {
      window.clearTimeout(heartbeatTimeoutTimer);
    }

    heartbeatTimeoutTimer = window.setTimeout(() => {
      if (socket?.readyState === WebSocket.OPEN) {
        callbacks.onError?.(new Error("WebSocket heartbeat timed out."));
        socket.close(4000, "Heartbeat timeout");
      }
    }, settings.heartbeatTimeoutMs);
  };

  const sendHeartbeat = () => {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      return;
    }

    try {
      socket.send(JSON.stringify({ type: "ping", timestamp: new Date().toISOString() }));
      scheduleHeartbeatTimeout();
    } catch (error) {
      callbacks.onError?.(normalizeSocketError(error));
    }
  };

  const startHeartbeat = () => {
    clearHeartbeat();
    heartbeatTimer = window.setInterval(sendHeartbeat, settings.heartbeatIntervalMs);
  };

  const reconnectDelayMs = () => {
    const baseDelay =
      settings.initialReconnectDelayMs *
      settings.backoffMultiplier ** Math.max(0, reconnectAttempts - 1);
    const cappedDelay = Math.min(baseDelay, settings.maxReconnectDelayMs);
    const jitter = Math.floor(Math.random() * settings.reconnectJitterMs);
    return cappedDelay + jitter;
  };

  const scheduleReconnect = (closeEvent) => {
    if (disposed || reconnectTimer !== null) {
      return;
    }

    if (reconnectAttempts >= settings.maxReconnectAttempts) {
      setState("failed", { closeEvent });
      callbacks.onReconnectStop?.({
        retryCount: reconnectAttempts,
        closeEvent,
      });
      return;
    }

    reconnectAttempts += 1;
    const delayMs = reconnectDelayMs();
    setState("reconnecting", {
      retryCount: reconnectAttempts,
      delayMs,
      closeEvent,
    });
    callbacks.onReconnect?.({
      retryCount: reconnectAttempts,
      delayMs,
      closeEvent,
    });

    reconnectTimer = window.setTimeout(() => {
      reconnectTimer = null;
      openSocket();
    }, delayMs);
  };

  const openSocket = () => {
    if (disposed) {
      return;
    }

    clearReconnectTimer();
    clearHeartbeat();
    detachSocket({ close: true, reason: "Replacing existing socket" });

    const nextState = hasConnected || reconnectAttempts > 0 ? "reconnecting" : "connecting";
    setState(nextState);

    let nextSocket;
    try {
      nextSocket = new WebSocket(buildFleetWebSocketUrl());
    } catch (error) {
      callbacks.onError?.(normalizeSocketError(error));
      setState("failed");
      callbacks.onReconnectStop?.({
        retryCount: reconnectAttempts,
        cause: normalizeSocketError(error),
      });
      return;
    }

    socket = nextSocket;

    nextSocket.onopen = () => {
      if (disposed || socket !== nextSocket) {
        return;
      }

      const wasReconnect = hasConnected || reconnectAttempts > 0;
      hasConnected = true;
      reconnectAttempts = 0;
      clearHeartbeat();
      setState("open", { wasReconnect });
      callbacks.onOpen?.({ wasReconnect });
      startHeartbeat();
    };

    nextSocket.onmessage = (event) => {
      if (socket !== nextSocket) {
        return;
      }

      try {
        const payload = safeParseMessage(event.data);
        if (payload.type === "pong") {
          if (heartbeatTimeoutTimer !== null) {
            window.clearTimeout(heartbeatTimeoutTimer);
            heartbeatTimeoutTimer = null;
          }
          callbacks.onHeartbeat?.(payload);
          return;
        }
        callbacks.onMessage?.(payload);
      } catch (error) {
        callbacks.onError?.(normalizeSocketError(error));
      }
    };

    nextSocket.onerror = () => {
      if (socket !== nextSocket) {
        return;
      }
      callbacks.onError?.(new Error("WebSocket connection error."));
    };

    nextSocket.onclose = (event) => {
      if (socket !== nextSocket) {
        return;
      }

      clearHeartbeat();
      socket = null;
      callbacks.onClose?.(event);

      if (disposed || event.code === 1000) {
        setState("closed", { closeEvent: event });
        return;
      }

      scheduleReconnect(event);
    };
  };

  openSocket();

  return {
    close(reason = "Client closed connection") {
      if (disposed) {
        return;
      }

      disposed = true;
      clearReconnectTimer();
      clearHeartbeat();

      const currentSocket = socket;
      detachSocket();
      if (
        currentSocket &&
        (currentSocket.readyState === WebSocket.OPEN || currentSocket.readyState === WebSocket.CONNECTING)
      ) {
        currentSocket.close(1000, reason);
      }

      setState("closed");
    },
    getState() {
      return state;
    },
  };
}
