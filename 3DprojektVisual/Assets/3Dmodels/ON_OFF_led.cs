using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;


public class ON_OFF_led : MonoBehaviour
{
    [SerializeField] private Material glowMaterial;
    [SerializeField] private Renderer objectToGlow;

    private bool isEmissionOn = false;
    private UdpClient udpClient;

    private void Start()
    {
        udpClient = new UdpClient(22345);
        Thread udpThread = new Thread(ReceiveUdpMessages);
        udpThread.IsBackground = true;
        udpThread.Start();
    }

    private void ReceiveUdpMessages()
    {
        IPEndPoint remoteEndPoint = new IPEndPoint(IPAddress.Any, 22345);

        try
        {
            while (true)
            {
                byte[] data = udpClient.Receive(ref remoteEndPoint);
                string message = Encoding.UTF8.GetString(data).Trim();

                if (message == "START")
                {
                    MainThreadExecutor.ExecuteOnMainThread(turnEmissionOn);
                }
                else if (message == "STOP")
                {
                    MainThreadExecutor.ExecuteOnMainThread(turnEmissionOff);
                }
            }
        }
        catch (SocketException e)
        {
            Debug.LogError("UDP Socket error: " + e.Message);
        }
    }

    public void turnEmissionOn()
    {
        glowMaterial.EnableKeyword("_EMISSION");
        isEmissionOn = true;
    }

    public void turnEmissionOff()
    {
        glowMaterial.DisableKeyword("_EMISSION");
        isEmissionOn = false;
    }

    private void OnApplicationQuit()
    {
        udpClient.Close();
    }
}
