import requests
import json
import urllib3

def extract_ipv4_prefixes_from_json_url(url, output_file="ipv4_prefixes.txt"):

    try:
        response = requests.get(url, verify=False) 
        response.raise_for_status() 
        data = response.json() # Parsea la respuesta JSON
        ipv4_prefixes = []

        # Función recursiva para buscar la clave 'ipv4Prefix' en diccionarios y listas anidados
        def find_ipv4_prefixes(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key == "ipv4Prefix":
                        ipv4_prefixes.append(value)
                    else:
                        find_ipv4_prefixes(value) # Recursión para diccionarios
            elif isinstance(obj, list):
                for item in obj:
                    find_ipv4_prefixes(item) # Recursión para listas

        find_ipv4_prefixes(data) # Inicia la búsqueda desde el objeto JSON raíz

        # Eliminar duplicados y mantener el orden (opcional)
        unique_ipv4_prefixes = sorted(list(set(ipv4_prefixes)))

        # Escribe los prefijos IPv4 en el archivo de salida
        with open(output_file, 'w') as f:
            for prefix in unique_ipv4_prefixes:
                f.write(f"{prefix}\n")

        print(f"Prefijos IPv4 extraídos y guardados en '{output_file}' exitosamente.")

    except requests.exceptions.RequestException as e:
        print(f"Error al acceder a la URL: {e}")
        print("Asegúrate de que la URL sea correcta y que tu conexión a internet funcione.")
        print("Si el error es 'SSLError', revisa las soluciones de verificación de certificados mencionadas anteriormente.")
    except json.JSONDecodeError:
        print("Error: La respuesta de la URL no es un JSON válido.")
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")

if __name__ == "__main__":
    json_url = "https://openai.com/chatgpt-user.json"
    extract_ipv4_prefixes_from_json_url(json_url)