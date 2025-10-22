# sg_sin_uso.py
from collections import defaultdict

def identificar_sg_sin_uso(sg_fallidos_data, mapeo_ec2_file='mapeo_ec2.txt', mapeo_otros_file='mapeo_otros.txt'):
    """
    Compara la lista maestra de SGs fallidos con los resultados de mapeo de recursos
    para encontrar SGs que no están en uso.
    """
    print("\n--- 4. Ejecutando: Identificación de SGs sin Uso ---")

    # 1. Obtener la lista maestra de SGs (SG ID: {metadata})
    sg_maestro = {item['SecurityGroupId']: item for item in sg_fallidos_data}
    
    # 2. Obtener todos los SGs que tienen alguna asociación
    sgs_en_uso = set()

    # Leer mapeo_ec2.txt (SG ID está en la posición 0)
    try:
        with open(mapeo_ec2_file, 'r', encoding='utf-8') as f:
            for line in f:
                sg_id = line.split(',')[0].strip()
                # Solo agregamos el SG si hay una instancia REAL (el ID es 'i-...')
                if 'i-' in line: 
                     sgs_en_uso.add(sg_id)
    except FileNotFoundError:
        print(f"⚠️ Advertencia: No se encontró {mapeo_ec2_file}. Asumiendo que todos los SGs están libres de EC2.")

    # Leer mapeo_otros.txt (SG ID está en la posición 0)
    try:
        with open(mapeo_otros_file, 'r', encoding='utf-8') as f:
            for line in f:
                sgs_en_uso.add(line.split(',')[0].strip())
    except FileNotFoundError:
        print(f"⚠️ Advertencia: No se encontró {mapeo_otros_file}. Asumiendo que todos los SGs están libres de otros recursos.")
    
    # 3. Comparación: SG fallido que NO está en el conjunto de SGs en uso
    sgs_libres = []
    for sg_id, data in sg_maestro.items():
        if sg_id not in sgs_en_uso:
            sgs_libres.append(data)

    # 4. Escribir el output a archivo (Objetivo 4)
    with open('sg_sin_uso.txt', 'w', encoding='utf-8') as f:
        for item in sgs_libres:
            # Formato: [SG ID], [Account ID], [Tag Entorno SG], [Tag Grupo SG]
            line = f"{item['SecurityGroupId']}, {item['AccountId']}, {item['EntornoSG']}, {item['GrupoSG']}\n"
            f.write(line)

    print(f"✅ Identificados {len(sgs_libres)} Security Groups que pueden ser eliminados.")
    print("   - Output guardado en sg_sin_uso.txt")