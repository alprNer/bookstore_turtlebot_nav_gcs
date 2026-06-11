#!/usr/bin/env python3
"""
QR kod PNG dosyaları ve Gazebo model dosyalarını üretir.
Çalıştırma: python3 scripts/generate_qr_models.py
"""
import os
import qrcode

BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "models")

# Model adı -> QR içeriği + Gazebo spawn pozisyonu (x y z yaw)
LOCATIONS = {
    "qr_danisma": {
        "content": "LOCATION=DANISMA",
        "x": 0.019945, "y": 5.01257, "z": 0.204313, "yaw": 3.1226,
    },
    "qr_okuma": {
        "content": "LOCATION=OKUMA",
        "x": -5.8828, "y": -3.99112, "z": 0.18468, "yaw": 0.4083,
    },
    "qr_roman": {
        "content": "LOCATION=ROMAN",
        "x": 7.40008, "y": 0.572527, "z": 0.193255, "yaw": -3.0911,
    },
    "qr_teknoloji": {
        "content": "LOCATION=TEKNOLOJI",
        "x": -0.728628, "y": -2.32182, "z": 0.218425, "yaw": 1.5937,
    },
}

MODEL_CONFIG = """\
<?xml version="1.0"?>
<model>
  <name>{name}</name>
  <version>1.0</version>
  <sdf version="1.6">model.sdf</sdf>
  <description>QR kod standı — {content}</description>
</model>
"""

MODEL_SDF = """\
<?xml version="1.0"?>
<sdf version="1.6">
  <model name="{name}">
    <static>true</static>
    <link name="link">
      <collision name="col">
        <geometry><box><size>0.003 0.28 0.28</size></box></geometry>
      </collision>
      <visual name="vis">
        <geometry><box><size>0.003 0.28 0.28</size></box></geometry>
        <material>
          <script>
            <uri>model://{name}/materials/scripts</uri>
            <uri>model://{name}/materials/textures</uri>
            <name>{mat}</name>
          </script>
        </material>
      </visual>
    </link>
  </model>
</sdf>
"""

MATERIAL_SCRIPT = """\
material {mat}
{{
  technique
  {{
    pass
    {{
      ambient 1 1 1 1
      diffuse 1 1 1 1
      texture_unit
      {{
        texture {tex}
        filtering none
      }}
    }}
  }}
}}
"""


def create_model(name, info):
    d         = os.path.join(MODELS_DIR, name)
    scripts_d = os.path.join(d, "materials", "scripts")
    textures_d = os.path.join(d, "materials", "textures")
    os.makedirs(scripts_d,  exist_ok=True)
    os.makedirs(textures_d, exist_ok=True)

    mat = "QR_" + name.replace("qr_", "").upper()
    tex = name + ".png"

    # QR PNG oluştur
    qr = qrcode.QRCode(version=2,
                       error_correction=qrcode.constants.ERROR_CORRECT_H,
                       box_size=20, border=2)
    qr.add_data(info["content"])
    qr.make(fit=True)
    qr.make_image(fill_color="black", back_color="white").save(
        os.path.join(textures_d, tex))

    open(os.path.join(d, "model.config"), "w").write(
        MODEL_CONFIG.format(name=name, content=info["content"]))
    open(os.path.join(d, "model.sdf"), "w").write(
        MODEL_SDF.format(name=name, mat=mat))
    open(os.path.join(scripts_d, name + ".material"), "w").write(
        MATERIAL_SCRIPT.format(mat=mat, tex=tex))

    print(f"  ✓  {name}  →  '{info['content']}'")


if __name__ == "__main__":
    os.makedirs(MODELS_DIR, exist_ok=True)
    print("QR modelleri oluşturuluyor...\n")
    for name, info in LOCATIONS.items():
        create_model(name, info)
    print("\nTamamlandı.")
