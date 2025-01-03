using UnityEngine;
using UnityEngine.UI;
using System.Net;
using System.Net.Sockets;
using System.Threading;

public class StreamReceiver : MonoBehaviour
{
    public RawImage rawImage;  // Reference to RawImage UI element
    public string udpIP = "127.0.0.1";  // IP of the sending Python app (localhost for now)
    public int udpPort = 12345;  // Port for the UDP connection

    private UdpClient udpClient;
    private Thread receiveThread;
    private bool isListening = false;
    private Texture2D texture;
    private byte[] receivedBytes;

    // To synchronize the image data between threads
    private bool imageReceived = false;
    private byte[] latestReceivedImage;

    void Start()
    {
        texture = new Texture2D(1, 1);  // Initial dummy texture
        rawImage.texture = texture;

        // Start listening for UDP packets
        StartListening();
    }

    void Update()
    {
        // If a new image is received, update the texture on the main thread
        if (imageReceived)
        {
            // Process the received image on the main thread
            ProcessReceivedData(latestReceivedImage);
            imageReceived = false;  // Reset the flag
        }
    }

    void StartListening()
    {
        isListening = true;
        // Start a new thread for receiving UDP packets
        receiveThread = new Thread(new ThreadStart(ListenForUdp));
        receiveThread.IsBackground = true;  // Make sure it runs in the background
        receiveThread.Start();
    }

    void ListenForUdp()
    {
        udpClient = new UdpClient(udpPort);
        udpClient.EnableBroadcast = true;
        IPEndPoint ipEndPoint = new IPEndPoint(IPAddress.Parse(udpIP), udpPort);

        Debug.Log("Waiting for connection...");

        try
        {
            while (true)
            {
                // Listen for incoming data
                receivedBytes = udpClient.Receive(ref ipEndPoint);
                if (receivedBytes != null && receivedBytes.Length > 0)
                {
                    // Pass the received data to the main thread
                    latestReceivedImage = receivedBytes;
                    imageReceived = true;
                }
            }
        }
        catch (System.Exception e)
        {
            // Handle exception (e.g., when the connection is lost)
            Debug.LogError("Error while receiving data: " + e.Message);
            // Restart the listener in case of any issues
            isListening = false;
            udpClient.Close();
            StartListening();  // Try to listen again for a new connection
        }
    }

    void ProcessReceivedData(byte[] data)
    {
        // Convert byte array to texture
        if (data.Length > 0)
        {
            // Create a new Texture2D
            Texture2D tempTexture = new Texture2D(2, 2); // Temporary texture to load the image data
            tempTexture.LoadImage(data);  // This will automatically convert the byte array into a Texture2D

            // Check if the texture is in BGR format (common in many image processing libraries)
            if (tempTexture.format == TextureFormat.RGB24)
            {
                // The texture data is in RGB format. But if you suspect it's BGR, we need to swap the colors
                SwapRedBlueChannels(tempTexture);
            }

            // Now that we've swapped the colors (if needed), assign the texture to the RawImage component
            texture = tempTexture;
            rawImage.texture = texture;
        }
    }

    void SwapRedBlueChannels(Texture2D texture)
    {
        Color[] pixels = texture.GetPixels();
        for (int i = 0; i < pixels.Length; i++)
        {
            // Swap red and blue channels
            float temp = pixels[i].r;
            pixels[i].r = pixels[i].b;
            pixels[i].b = temp;
        }
        texture.SetPixels(pixels);
        texture.Apply();
    }

    void OnApplicationQuit()
    {
        // Clean up when the application quits
        if (receiveThread != null && receiveThread.IsAlive)
        {
            receiveThread.Abort();
        }

        if (udpClient != null)
        {
            udpClient.Close();
        }
    }
}
