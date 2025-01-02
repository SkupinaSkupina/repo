using System.Collections;
using UnityEngine;
using System.Collections.Generic;

public class UnityMainThreadDispatcher : MonoBehaviour
{
    private static readonly Queue<System.Action> executionQueue = new Queue<System.Action>();

    public static UnityMainThreadDispatcher Instance { get; private set; }

    private void Awake()
    {
        if (Instance == null)
        {
            Instance = this;
        }
    }

    private void Update()
    {
        while (executionQueue.Count > 0)
        {
            var action = executionQueue.Dequeue();
            action();
        }
    }

    public void Enqueue(System.Action action)
    {
        lock (executionQueue)
        {
            executionQueue.Enqueue(action);
        }
    }
}
