import os
import re
import shutil
import datetime

# Constantes de caminhos
BASE_PATH = r"z:\Base-MonteAzul\server-data\resources"

FILES = {
    "config_garage": {
        "path": os.path.join(BASE_PATH, r"[scripts]\skips_garagem\config\config_garage.lua"),
        "pattern": r"Config\.vehList\s*=\s*\{",
        "format": "\t{{ hash = GetHashKey(\"{spawn}\"), name = '{spawn}', price = {price}, banido = false, modelo = '{name}', capacidade = {capacity}, tipo = '{type}' }},"
    },
    "config_server": {
        "path": os.path.join(BASE_PATH, r"[scripts]\skips_inventario\server-side\Config_server.lua"),
        "pattern": r"vehList\s*=\s*\{",
        "format": "\t{{ hash = GetHashKey(\"{spawn}\"), name = \"{spawn}\", capacidade = {capacity} }},"
    },
    "basic_garage": {
        "path": os.path.join(BASE_PATH, r"[vrp]\vrp\client\basic_garage.lua"),
        "pattern": r"local\s+vehList\s*=\s*\{",
        "format": "\t{{ ['hash'] = GetHashKey(\"{spawn}\"), ['name'] = '{spawn}', ['banned'] = false }},"
    },
    "inventory": {
        "path": os.path.join(BASE_PATH, r"[vrp]\vrp\modules\inventory.lua"),
        "pattern": r"vehs\.vehglobal\s*=\s*\{",
        "format": "\t[\"{spawn}\"] = {{ ['name'] = \"{name}\", ['price'] = {price}, ['tipo'] = \"{type}\",  ['hash'] = GetHashKey(\"{spawn}\"), ['banned'] = false }},"
    }
}

def backup_file(filepath):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{filepath}.{timestamp}.bak"
    try:
        shutil.copy2(filepath, backup_path)
        print(f"[OK] Backup criado: {backup_path}")
    except Exception as e:
        print(f"[ERRO] Falha ao criar backup de {filepath}: {e}")
        return False
    return True

def append_to_table(filepath, table_start_pattern, content_to_append, spawn):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Verifica duplicatas (busca pelo spawn)
        # O format tem o spawn como parte da string, então podemos pegar do próprio 'content_to_append'
        # ou apenas checar se a string formatada para inserção já existe parcialmente
        if f'"{spawn}"' in content or f"'{spawn}'" in content or f'GetHashKey("{spawn}")' in content:
            print(f"[AVISO] O veículo '{spawn}' parece já existir em {os.path.basename(filepath)}. Pulando inserção.")
            return False

        match = re.search(table_start_pattern, content)
        if not match:
            print(f"[ERRO] Tabela não encontrada em {os.path.basename(filepath)} usando padrão {table_start_pattern}")
            return False
        
        start_index = match.end()
        brace_count = 1
        i = start_index
        while i < len(content):
            if content[i] == '{':
                brace_count += 1
            elif content[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    break
            i += 1
        
        if brace_count != 0:
            print(f"[ERRO] Não foi possível encontrar o fim da tabela em {os.path.basename(filepath)}")
            return False
        
        # Encontra a última linha antes da chave de fechamento para manter formatação (opcional)
        insertion_point = i
        
        # Insere antes da chave de fechamento
        new_content = content[:insertion_point] + content_to_append + "\n" + content[insertion_point:]
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"[OK] Veículo inserido em {os.path.basename(filepath)}")
        return True
    except Exception as e:
        print(f"[ERRO] Falha ao processar {filepath}: {e}")
        return False

def main():
    print("="*50)
    print("SISTEMA DE ADIÇÃO DE VEÍCULOS - MONTE AZUL".center(50))
    print("="*50)
    
    spawn = input("1. Nome de spawn (ex: eclipsespydertrg): ").strip()
    name = input("2. Nome exibido (ex: Eclipse Spyder): ").strip()
    
    while True:
        try:
            capacity = int(input("3. Capacidade do porta-malas (ex: 150): ").strip())
            break
        except ValueError:
            print("Por favor, insira um número válido para a capacidade.")
            
    while True:
        try:
            price = int(input("4. Preço (ex: 0 para carros vips/faccoes): ").strip())
            break
        except ValueError:
            print("Por favor, insira um número válido para o preço.")
            
    tipo = input("5. Tipo (ex: carros, motos, work, barcos, helicoptero): ").strip()
    
    print("\nIniciando processo de automação...")
    
    for key, info in FILES.items():
        filepath = info["path"]
        pattern = info["pattern"]
        line_format = info["format"].format(
            spawn=spawn,
            name=name,
            capacity=capacity,
            price=price,
            type=tipo
        )
        
        if not os.path.exists(filepath):
            print(f"[ERRO] Arquivo não encontrado: {filepath}")
            continue
            
        if backup_file(filepath):
            append_to_table(filepath, pattern, line_format, spawn)

    print("="*50)
    print("Processo finalizado!".center(50))
    print("="*50)

if __name__ == "__main__":
    main()
