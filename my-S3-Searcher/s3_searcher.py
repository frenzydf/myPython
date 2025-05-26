import boto3
import os

def process_s3_buckets(file_list_path, output_file_path):
    s3 = boto3.client('s3')
    found_files = []
    print("Obteniendo la lista de buckets de S3...")
    try:
        response = s3.list_buckets()
        buckets = [bucket['Name'] for bucket in response['Buckets']]
        print(f"Se encontraron {len(buckets)} buckets.")
    except Exception as e:
        print(f"Error al listar los buckets: {e}")
        return

    print(f"Cargando la lista de archivos a buscar desde: {file_list_path}...")
    try:
        with open(file_list_path, 'r') as f:
            files_to_find = [line.strip() for line in f if line.strip()]
        print(f"Se encontraron {len(files_to_find)} archivos para buscar.")
    except FileNotFoundError:
        print(f"Error: El archivo '{file_list_path}' no fue encontrado.")
        return
    except Exception as e:
        print(f"Error al leer el archivo de la lista: {e}")
        return

    if not files_to_find:
        print("La lista de archivos a buscar está vacía. No se realizará ninguna búsqueda.")
        return

    print("Iniciando la búsqueda de archivos en los buckets...")
    for bucket_name in buckets:
        print(f"Buscando en el bucket: {bucket_name}")
        try:
            paginator = s3.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=bucket_name)
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        object_key = obj['Key']
                        object_filename = os.path.basename(object_key)
                        if object_filename in files_to_find:
                            found_files.append(f"Archivo: {object_key}, Bucket: {bucket_name}")
                            print(f"  ¡Encontrado! Archivo: {object_key} en Bucket: {bucket_name}")

        except Exception as e:
            print(f"  Error al listar objetos en el bucket '{bucket_name}': {e}")
            continue

    print(f"Generando el archivo de resultados en: {output_file_path}...")
    try:
        with open(output_file_path, 'w') as f:
            if found_files:
                for entry in found_files:
                    f.write(entry + '\n')
                print(f"Se encontraron y registraron {len(found_files)} archivos.")
            else:
                f.write("No se encontraron los archivos especificados en ningún bucket.\n")
                print("No se encontraron los archivos especificados.")
        print("Proceso completado. Revisa el archivo de salida para los resultados.")
    except Exception as e:
        print(f"Error al escribir el archivo de salida: {e}")

if __name__ == "__main__":
    files_to_search_txt = 'files_to_search.txt'
    output_results_txt = 'found_s3_files.txt'
    if not os.path.exists(files_to_search_txt):
        print(f"Por favor, edita '{files_to_search_txt}' con los nombres de archivos reales que deseas buscar.")
        print("Luego, vuelve a ejecutar el script.")
    else:
        print(f"Usando el archivo de lista de búsqueda existente: {files_to_search_txt}")

    process_s3_buckets(files_to_search_txt, output_results_txt)