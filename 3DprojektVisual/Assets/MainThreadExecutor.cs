using System;
using System.Collections.Generic;
using UnityEngine;

public class MainThreadExecutor : MonoBehaviour
{
    private static Queue<Action> actions = new Queue<Action>();

    // Dodaj naloge v èakalno vrsto
    public static void ExecuteOnMainThread(Action action)
    {
        lock (actions)
        {
            actions.Enqueue(action);
        }
    }

    // Izvedi naloge v glavni nit
    private void Update()
    {
        lock (actions)
        {
            while (actions.Count > 0)
            {
                actions.Dequeue().Invoke();
            }
        }
    }
}
