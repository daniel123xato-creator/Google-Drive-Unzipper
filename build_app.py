#!/usr/bin/env python3
"""
build_app.py - Constrói o aplicativo nativo macOS 'Descompactador Drive.app'
com ícone personalizado, Info.plist e inicializador executável.
"""

import os
import shutil
import subprocess
import struct

APP_NAME = "Descompactador Drive"
BUNDLE_DIR = f"{APP_NAME}.app"
CONTENTS_DIR = os.path.join(BUNDLE_DIR, "Contents")
MACOS_DIR = os.path.join(CONTENTS_DIR, "MacOS")
RESOURCES_DIR = os.path.join(CONTENTS_DIR, "Resources")

def generate_icon(output_icns_path: str):
    """Gera um ícone nativo macOS .icns moderno em alta resolução."""
    print("-> Gerando ícone do aplicativo...")
    
    size = 1024
    ppm_path = "temp_icon_1024.ppm"
    png_path = "temp_icon_1024.png"
    
    # Gera imagem PPM 1024x1024 com degradê azul moderno e símbolo de descompactação
    with open(ppm_path, "wb") as f:
        header = f"P6\n{size} {size}\n255\n"
        f.write(header.encode("ascii"))
        
        cx, cy = size // 2, size // 2
        r_box = 440
        radius_corner = 210
        
        pixel_bytes = bytearray(size * size * 3)
        idx = 0
        
        for y in range(size):
            for x in range(size):
                # Distância do centro para criar retângulo arredondado estilo Apple
                dx = abs(x - cx)
                dy = abs(y - cy)
                
                in_squircle = False
                if dx <= (r_box - radius_corner) and dy <= r_box:
                    in_squircle = True
                elif dy <= (r_box - radius_corner) and dx <= r_box:
                    in_squircle = True
                elif dx > (r_box - radius_corner) and dy > (r_box - radius_corner):
                    corner_dx = dx - (r_box - radius_corner)
                    corner_dy = dy - (r_box - radius_corner)
                    if (corner_dx**2 + corner_dy**2) <= radius_corner**2:
                        in_squircle = True
                        
                if in_squircle:
                    factor = (y / size)
                    # Azul moderno Apple / Google Drive gradient
                    red = int(14 * (1 - factor) + 0 * factor)
                    green = int(120 * (1 - factor) + 70 * factor)
                    blue = int(250 * (1 - factor) + 210 * factor)
                    
                    # Caixa de arquivo (base)
                    is_box_outline = (290 <= x <= 734) and (530 <= y <= 770)
                    is_box_fill = (316 <= x <= 708) and (556 <= y <= 744)
                    
                    # Seta de descompactação / extração
                    is_stem = (480 <= x <= 544) and (310 <= y <= 580)
                    is_arrowhead = False
                    if 170 <= y <= 350:
                        tri_w = (y - 170) * 1.3
                        if (512 - tri_w) <= x <= (512 + tri_w):
                            is_arrowhead = True
                            
                    # Abas abertas da caixa
                    is_flap_l = (210 <= x <= 320) and (430 <= y <= 540) and (abs((y - 430) - (x - 210)) < 26)
                    is_flap_r = (704 <= x <= 814) and (430 <= y <= 540) and (abs((y - 430) + (x - 814)) < 26)
                    
                    # Faixas decorativas (Cores do Drive: Amarelo, Verde, Azul)
                    is_drive_strip = (340 <= x <= 684) and (600 <= y <= 630)
                    
                    if is_arrowhead or is_stem:
                        red, green, blue = 255, 255, 255
                    elif is_flap_l or is_flap_r:
                        red, green, blue = 255, 204, 0
                    elif is_drive_strip:
                        red, green, blue = 52, 168, 83 # Verde Drive
                    elif is_box_fill:
                        red, green, blue = 2, 40, 110 # Azul profundo interior
                    elif is_box_outline:
                        red, green, blue = 255, 187, 0 # Dourado Drive
                else:
                    # Fundo neutro
                    red, green, blue = 245, 245, 247
                    
                pixel_bytes[idx] = red
                pixel_bytes[idx+1] = green
                pixel_bytes[idx+2] = blue
                idx += 3
                
        f.write(pixel_bytes)

    # Converte PPM base para PNG 1024
    subprocess.run(["sips", "-s", "format", "png", ppm_path, "--out", png_path], check=True, stdout=subprocess.DEVNULL)
    
    # Gera resoluções chave e empacota diretamente no formato Apple ICNS
    sizes_and_tags = [
        (128, b'ic07', "icon_128.png"),
        (256, b'ic08', "icon_256.png"),
        (512, b'ic09', "icon_512.png"),
        (1024, b'ic10', "icon_1024.png"),
    ]
    
    chunks = []
    temp_pngs = [png_path]
    for sz, tag, temp_name in sizes_and_tags:
        if sz == 1024:
            dest_file = png_path
        else:
            dest_file = temp_name
            temp_pngs.append(dest_file)
            subprocess.run(["sips", "-z", str(sz), str(sz), png_path, "--out", dest_file], check=True, stdout=subprocess.DEVNULL)
            
        with open(dest_file, "rb") as f_png:
            data = f_png.read()
        chunk = tag + struct.pack('>I', len(data) + 8) + data
        chunks.append(chunk)

    body = b''.join(chunks)
    header = b'icns' + struct.pack('>I', len(body) + 8)
    with open(output_icns_path, "wb") as f_out:
        f_out.write(header + body)
        
    # Limpeza
    for p in temp_pngs:
        if os.path.exists(p):
            os.remove(p)
    if os.path.exists(ppm_path):
        os.remove(ppm_path)
        
    print(f"-> Ícone .icns nativo gerado: {output_icns_path}")


def build_app():
    print(f"=== Montando pacote macOS: {BUNDLE_DIR} ===")
    
    if os.path.exists(BUNDLE_DIR):
        shutil.rmtree(BUNDLE_DIR)
        
    os.makedirs(MACOS_DIR, exist_ok=True)
    os.makedirs(RESOURCES_DIR, exist_ok=True)
    
    # 1. Copia os módulos Python para Resources
    shutil.copy2("core_unpacker.py", RESOURCES_DIR)
    shutil.copy2("app_gui.py", RESOURCES_DIR)
    
    # 2. Cria o arquivo Info.plist
    info_plist_path = os.path.join(CONTENTS_DIR, "Info.plist")
    plist_content = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>Descompactador Drive</string>
    <key>CFBundleDisplayName</key>
    <string>Descompactador Drive</string>
    <key>CFBundleIdentifier</key>
    <string>com.auraworkshop.driveunpacker</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>CFBundleExecutable</key>
    <string>launcher</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSMinimumSystemVersion</key>
    <string>10.13</string>
</dict>
</plist>
"""
    with open(info_plist_path, "w", encoding="utf-8") as f:
        f.write(plist_content)
        
    # 3. Cria o executável em MacOS/launcher
    launcher_path = os.path.join(MACOS_DIR, "launcher")
    launcher_content = """#!/bin/bash
DIR="$(cd "$(dirname "$0")/../Resources" && pwd)"
export PYTHONPATH="$DIR:$PYTHONPATH"

# Localiza o Python 3 disponível no sistema
if [ -x "/Library/Frameworks/Python.framework/Versions/3.14/bin/python3" ]; then
    PYTHON_BIN="/Library/Frameworks/Python.framework/Versions/3.14/bin/python3"
elif [ -x "/usr/local/bin/python3" ]; then
    PYTHON_BIN="/usr/local/bin/python3"
elif [ -x "/opt/homebrew/bin/python3" ]; then
    PYTHON_BIN="/opt/homebrew/bin/python3"
elif which python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(which python3)"
else
    PYTHON_BIN="/usr/bin/python3"
fi

exec "$PYTHON_BIN" "$DIR/app_gui.py" "$@"
"""
    with open(launcher_path, "w", encoding="utf-8") as f:
        f.write(launcher_content)
        
    os.chmod(launcher_path, 0o755)
    
    # 4. Gera o ícone .icns
    icns_path = os.path.join(RESOURCES_DIR, "AppIcon.icns")
    try:
        generate_icon(icns_path)
    except Exception as e:
        print(f"Aviso ao gerar ícone: {e}")

    print(f"\n✅ APLICATIVO CRIADO COM SUCESSO:")
    print(f"   -> {os.path.abspath(BUNDLE_DIR)}")
    print("Você pode dar um duplo clique para abrir ou arrastá-lo para a pasta /Applications!\n")

if __name__ == "__main__":
    build_app()
