# main.py
# La función get_profile_to_account_map ya no es necesaria

import obtener_sg_fallidos
import mapear_ec2
import mapear_otros
import sg_sin_uso

# ==============================================================================
# CONFIGURACIÓN MAESTRA
# ==============================================================================
AWS_REGION_TO_USE = "us-east-1" 

def main():
    print("==================================================")
    print("🚀 INICIANDO AUDITORÍA UNIFICADA DE SG FALLIDOS")
    print("==================================================")
    
    # 1. OBTENER DATOS MAESTROS Y TAGS DE SG
    # La función de obtención ahora hace el mapeo internamente
    sg_fallidos_data = obtener_sg_fallidos.obtener_sg_fallidos(AWS_REGION_TO_USE)
    if not sg_fallidos_data:
        print("\nProceso terminado: No se encontraron Security Groups fallidos en las cuentas auditables.")
        return
    
    # 2. MAPEO A INSTANCIAS EC2
    mapear_ec2.mapear_ec2(sg_fallidos_data, AWS_REGION_TO_USE)
    
    # 3. MAPEO A OTROS RECURSOS
    mapear_otros.mapear_otros_recursos(sg_fallidos_data, AWS_REGION_TO_USE)

    # 4. IDENTIFICACIÓN DE SGs SIN USO (Depende de los outputs de 2 y 3)
    sg_sin_uso.identificar_sg_sin_uso(sg_fallidos_data)

    print("\n==================================================")
    print("✅ AUDITORÍA COMPLETA FINALIZADA.")
    print("   Verifique los archivos: sg_fallidos.txt, mapeo_ec2.txt, mapeo_otros.txt, sg_sin_uso.txt")
    print("==================================================")

if __name__ == "__main__":
    main()