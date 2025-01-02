using System;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using UnityEngine;
using UnityEngine.UI;

public class ImageReceiver : MonoBehaviour
{
    public int port = 12345;  // Port that server will listen on
    private TcpListener listener;
    private Thread listenerThread;
    private bool isRunning = true;

    public RawImage rawImageComponent;  // The RawImage component to display the texture on
    private TcpClient currentClient;    // Holds the current client

    private MemoryStream bufferStream = new MemoryStream(); // Buffer to store incoming data

    void Start()
    {
        // Start TCP server thread
        listenerThread = new Thread(StartServer);
        listenerThread.IsBackground = true;
        listenerThread.Start();
    }

    void StartServer()
    {
        try
        {
            listener = new TcpListener(IPAddress.Any, port);
            listener.Start();
            Debug.Log($"Server started on port {port}");

            while (isRunning)
            {
                if (listener.Pending())
                {
                    currentClient = listener.AcceptTcpClient();
                    Debug.Log("Client connected");

                    // Start handling the connected client in a separate thread
                    Thread clientThread = new Thread(() => HandleClient(currentClient));
                    clientThread.IsBackground = true;
                    clientThread.Start();
                }
                Thread.Sleep(100);  // Check if clients are connecting
            }
        }
        catch (Exception ex)
        {
            Debug.LogError($"Error in server: {ex.Message}");
        }
        finally
        {
            listener?.Stop();
        }
    }

    private readonly object bufferLock = new object(); // Lock for thread safety

    void HandleClient(TcpClient client)
    {
        try
        {
            using (NetworkStream stream = client.GetStream())
            {
                byte[] buffer = new byte[4096];
                int bytesRead;

                while (client.Connected && isRunning)
                {
                    while ((bytesRead = stream.Read(buffer, 0, buffer.Length)) > 0)
                    {
                        lock (bufferLock)
                        {
                            bufferStream.Write(buffer, 0, bytesRead); // Safely write to buffer
                        }

                        if (TryParseImage())
                        {
                            byte[] imageData;
                            lock (bufferLock)
                            {
                                imageData = bufferStream.ToArray();
                            }

                            UnityMainThreadDispatcher.Instance.Enqueue(() =>
                            {
                                LoadAndApplyTexture(imageData);
                            });

                            lock (bufferLock)
                            {
                                bufferStream.SetLength(0);  // Clear buffer
                            }
                        }
                    }

                    Thread.Sleep(10);
                }
            }
        }
        catch (Exception ex)
        {
            Debug.LogError($"Error handling client: {ex.Message}");
        }
        finally
        {
            client.Close();
            Debug.Log("Client disconnected");
        }
    }

    // Basic logic for determining a complete image frame
    bool TryParseImage()
    {
        const int minImageSize = 1024;  // Minimum image size, adjust based on your use case
        return bufferStream.Length > minImageSize && IsEndOfImage(bufferStream);
    }

    bool IsEndOfImage(MemoryStream buffer)
    {
        byte[] data = buffer.ToArray();

        // For JPEG image files, check for JPEG end marker
        return data.Length > 2 && data[data.Length - 2] == 0xFF && data[data.Length - 1] == 0xD9; // JPEG end marker
    }

    void LoadAndApplyTexture(byte[] imageData)
    {
        if (imageData.Length == 0)
        {
            Debug.LogError("Received empty image data.");
            return;
        }

        // Debug the content of image data further, check if it starts with a valid image header
        Debug.Log($"Starting bytes: {BitConverter.ToString(imageData.Take(10).ToArray())}");

        // Verify that it matches known image formats (JPEG, PNG etc.)
        if (imageData.Take(3).SequenceEqual(new byte[] { 0xFF, 0xD8, 0xFF })) // JPEG header
        {
            Debug.Log("JPEG image detected.");
        }
        else if (imageData.Take(4).SequenceEqual(new byte[] { 0x89, 0x50, 0x4E, 0x47 })) // PNG header
        {
            Debug.Log("PNG image detected.");
        }

        Texture2D texture = new Texture2D(2, 2);
        if (texture.LoadImage(imageData))  // Load the image from bytes
        {
            ApplyImage(texture);
        }
        else
        {
            Debug.LogError("Failed to load image data into Texture2D.");
        }
    }


    void ApplyImage(Texture2D texture)
    {
        if (rawImageComponent == null)
        {
            Debug.LogError("RawImage component is not assigned.");
            return;
        }

        rawImageComponent.texture = texture;
        rawImageComponent.SetNativeSize();  // Automatically adjust the RawImage to the size of the texture
        Debug.Log("Texture applied to RawImage.");
    }

    void OnApplicationQuit()
    {
        isRunning = false;

        // Shutdown listeners and threads carefully
        listener?.Stop();
        listenerThread?.Join();

        if (currentClient?.Connected == true)
        {
            currentClient.Close();
        }
    }
}
