using System;
using System.Collections;
using System.Collections.Generic;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine;

#if !UNITY_WEBGL || UNITY_EDITOR
using System.Net.WebSockets;
#endif

namespace SAM.Avatar
{
    /// <summary>
    /// WebSocket connection to Warp Open terminal.
    /// Handles bidirectional communication with SAM AI.
    /// </summary>
    public class SAMConnection : MonoBehaviour
    {
        public bool IsConnected { get; private set; }
        public string ClientId { get; private set; }

        public event Action OnConnected;
        public event Action OnDisconnected;
        public event Action<SAMMessage> OnMessageReceived;
        public event Action<string> OnError;

#if !UNITY_WEBGL || UNITY_EDITOR
        private ClientWebSocket _webSocket;
        private CancellationTokenSource _cancellation;
#endif

        private Queue<SAMMessage> _messageQueue = new Queue<SAMMessage>();
        private Queue<string> _sendQueue = new Queue<string>();
        private bool _isConnecting;

        private void Update()
        {
            // Process received messages on main thread
            lock (_messageQueue)
            {
                while (_messageQueue.Count > 0)
                {
                    var msg = _messageQueue.Dequeue();
                    OnMessageReceived?.Invoke(msg);
                }
            }

            // Process send queue
            ProcessSendQueue();
        }

        public void Connect(string host, int port)
        {
            if (IsConnected || _isConnecting) return;
            StartCoroutine(ConnectAsync(host, port));
        }

        public void Disconnect()
        {
#if !UNITY_WEBGL || UNITY_EDITOR
            _cancellation?.Cancel();

            if (_webSocket != null && _webSocket.State == WebSocketState.Open)
            {
                try
                {
                    _webSocket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Client disconnecting", CancellationToken.None);
                }
                catch { }
            }

            _webSocket = null;
#endif
            IsConnected = false;
            OnDisconnected?.Invoke();
        }

        private IEnumerator ConnectAsync(string host, int port)
        {
            _isConnecting = true;
            string uri = $"ws://{host}:{port}";

            Debug.Log($"[SAM] Connecting to {uri}...");

#if !UNITY_WEBGL || UNITY_EDITOR
            _webSocket = new ClientWebSocket();
            _cancellation = new CancellationTokenSource();

            var connectTask = _webSocket.ConnectAsync(new Uri(uri), _cancellation.Token);

            while (!connectTask.IsCompleted)
            {
                yield return null;
            }

            if (connectTask.IsFaulted)
            {
                Debug.LogError($"[SAM] Connection failed: {connectTask.Exception?.Message}");
                OnError?.Invoke(connectTask.Exception?.Message);
                _isConnecting = false;
                yield break;
            }

            IsConnected = true;
            _isConnecting = false;

            Debug.Log("[SAM] Connected!");

            // Send registration
            SendRegistration();

            // Start receiving
            StartCoroutine(ReceiveLoop());

            OnConnected?.Invoke();
#else
            Debug.LogWarning("[SAM] WebSocket not supported in WebGL builds - use JavaScript bridge");
            _isConnecting = false;
            yield break;
#endif
        }

        private void SendRegistration()
        {
            var registration = new
            {
                type = "register",
                client = "unity",
                platform = Application.platform.ToString(),
                capabilities = new[] { "animation", "morph_targets", "physics", "lipsync" }
            };

            Send(JsonUtility.ToJson(new RegistrationMessage
            {
                type = "register",
                client = "unity",
                platform = Application.platform.ToString()
            }));
        }

#if !UNITY_WEBGL || UNITY_EDITOR
        private IEnumerator ReceiveLoop()
        {
            var buffer = new byte[8192];

            while (IsConnected && _webSocket?.State == WebSocketState.Open)
            {
                var receiveTask = ReceiveMessage(buffer);

                while (!receiveTask.IsCompleted)
                {
                    yield return null;
                }

                if (receiveTask.IsFaulted)
                {
                    Debug.LogError($"[SAM] Receive error: {receiveTask.Exception?.Message}");
                    break;
                }

                string message = receiveTask.Result;
                if (!string.IsNullOrEmpty(message))
                {
                    ProcessMessage(message);
                }
            }

            IsConnected = false;
            OnDisconnected?.Invoke();
        }

        private async Task<string> ReceiveMessage(byte[] buffer)
        {
            try
            {
                var result = await _webSocket.ReceiveAsync(
                    new ArraySegment<byte>(buffer),
                    _cancellation.Token
                );

                if (result.MessageType == WebSocketMessageType.Close)
                {
                    return null;
                }

                return Encoding.UTF8.GetString(buffer, 0, result.Count);
            }
            catch (OperationCanceledException)
            {
                return null;
            }
            catch (Exception e)
            {
                Debug.LogError($"[SAM] Receive exception: {e.Message}");
                return null;
            }
        }
#endif

        private void ProcessMessage(string json)
        {
            try
            {
                var message = JsonUtility.FromJson<SAMMessage>(json);

                // Handle registration response
                if (message.type == "registered")
                {
                    ClientId = message.client_id;
                    Debug.Log($"[SAM] Registered with ID: {ClientId}");
                    return;
                }

                // Queue for main thread processing
                lock (_messageQueue)
                {
                    _messageQueue.Enqueue(message);
                }
            }
            catch (Exception e)
            {
                Debug.LogWarning($"[SAM] Failed to parse message: {e.Message}\n{json}");
            }
        }

        public void Send(string message)
        {
            lock (_sendQueue)
            {
                _sendQueue.Enqueue(message);
            }
        }

        public void SendEvent(string eventType, Dictionary<string, object> data)
        {
            var evt = new SAMEvent
            {
                type = eventType,
                timestamp = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()
            };

            // Convert data to JSON manually since Dictionary isn't directly serializable
            string dataJson = "{";
            foreach (var kvp in data)
            {
                dataJson += $"\"{kvp.Key}\":{JsonUtility.ToJson(kvp.Value)},";
            }
            dataJson = dataJson.TrimEnd(',') + "}";

            string json = $"{{\"type\":\"{eventType}\",\"data\":{dataJson},\"timestamp\":{evt.timestamp}}}";
            Send(json);
        }

        private void ProcessSendQueue()
        {
#if !UNITY_WEBGL || UNITY_EDITOR
            if (_webSocket?.State != WebSocketState.Open) return;

            lock (_sendQueue)
            {
                while (_sendQueue.Count > 0)
                {
                    string message = _sendQueue.Dequeue();
                    byte[] bytes = Encoding.UTF8.GetBytes(message);

                    try
                    {
                        _webSocket.SendAsync(
                            new ArraySegment<byte>(bytes),
                            WebSocketMessageType.Text,
                            true,
                            CancellationToken.None
                        );
                    }
                    catch (Exception e)
                    {
                        Debug.LogError($"[SAM] Send error: {e.Message}");
                    }
                }
            }
#endif
        }

        private void OnDestroy()
        {
            Disconnect();
        }

        private void OnApplicationQuit()
        {
            Disconnect();
        }
    }

    #region Message Types

    [Serializable]
    public class RegistrationMessage
    {
        public string type;
        public string client;
        public string platform;
    }

    [Serializable]
    public class SAMMessage
    {
        public string type;
        public string client_id;

        // Animation
        public string animation;
        public float intensity = 1f;
        public bool loop = true;
        public float duration;

        // Emotion
        public string emotion;
        public SerializableDictionary expression;

        // Morph targets
        public SerializableDictionary morph_targets;
        public float transition = 0.3f;

        // Lip sync
        public List<LipSyncFrame> lipSyncData;
        public float totalDuration;
        public bool stop;

        // Gesture
        public string gesture;
        public string hand;

        // Look
        public SerializableDictionary target;

        // Custom
        public string action;
        public SerializableDictionary customData;
    }

    [Serializable]
    public class SAMEvent
    {
        public string type;
        public long timestamp;
    }

    [Serializable]
    public class SerializableDictionary : ISerializationCallbackReceiver
    {
        [SerializeField] private List<string> keys = new List<string>();
        [SerializeField] private List<float> values = new List<float>();

        private Dictionary<string, float> _dictionary = new Dictionary<string, float>();

        public bool TryGetValue(string key, out float value) => _dictionary.TryGetValue(key, out value);
        public float this[string key] => _dictionary[key];
        public IEnumerable<KeyValuePair<string, float>> Items => _dictionary;
        public bool ContainsKey(string key) => _dictionary.ContainsKey(key);

        public void OnBeforeSerialize()
        {
            keys.Clear();
            values.Clear();
            foreach (var kvp in _dictionary)
            {
                keys.Add(kvp.Key);
                values.Add(kvp.Value);
            }
        }

        public void OnAfterDeserialize()
        {
            _dictionary.Clear();
            for (int i = 0; i < Mathf.Min(keys.Count, values.Count); i++)
            {
                _dictionary[keys[i]] = values[i];
            }
        }
    }

    #endregion
}
