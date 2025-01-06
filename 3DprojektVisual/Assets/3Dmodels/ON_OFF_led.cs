using System.Collections;
using System.Collections.Generic;
using System.Net;
using System.Net.Sockets;
using UnityEngine;

public class ON_OFF_led : MonoBehaviour
{
    [SerializeField] private Material glowMaterial;  // Material, ki ga bomo spreminjali
    [SerializeField] private Renderer objectToGlow;  // Objekt, ki ima material

    private bool isEmissionOn = false;  // Spremlja stanje emisije

    private void Update()
    {
        // Preverite, ali je tipka 'E' pritisnjena
        if (Input.GetKeyDown(KeyCode.E))
        {
            // Preklop emisije ob pritisku na 'E'
            if (isEmissionOn)
            {
                turnEmissionOff();
            }
            else
            {
                turnEmissionOn();
            }
        }
    }

    // Funkcija za izklop emisije
    public void turnEmissionOff()
    {
        glowMaterial.DisableKeyword("_EMISSION");
        isEmissionOn = false;
    }

    // Funkcija za vklop emisije
    public void turnEmissionOn()
    {
        glowMaterial.EnableKeyword("_EMISSION");
        isEmissionOn = true;
    }

}
