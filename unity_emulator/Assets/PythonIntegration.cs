using System.Diagnostics;
using UnityEngine;

public class PythonIntegration : MonoBehaviour
{
    private Process pythonProcess;

    void Start()
    {
        // Path to Python executable and the script you want to run
        string pythonPath = "C:\\path\\to\\python.exe"; // Replace with the correct path
        string scriptPath = "C:\\path\\to\\your\\python_script.py"; // Path to your Python script

        // Start the Python script in the background
        ProcessStartInfo startInfo = new ProcessStartInfo
        {
            FileName = pythonPath,
            Arguments = scriptPath,
            CreateNoWindow = true,          // Don't create a new console window
            UseShellExecute = false,       // Required to redirect output streams
            RedirectStandardOutput = true, // To capture the Python app's output
            RedirectStandardError = true
        };

        pythonProcess = new Process { StartInfo = startInfo };
        pythonProcess.Start();
    }

    void OnApplicationQuit()
    {
        // Ensure the Python process is closed when Unity quits
        if (pythonProcess != null && !pythonProcess.HasExited)
        {
            pythonProcess.Kill();
        }
    }
}
