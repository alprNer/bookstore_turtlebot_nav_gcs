<div align="center">

[Türkçe](#türkçe) | [English](#english)

---

<h1>🤖 Bookstore TurtleBot3 Navigation & GCS</h1>

<p><strong>Ubuntu 20.04, ROS Noetic, TurtleBot3 ve Gazebo Simülasyon Ortamında<br>QR Kod Doğrulamalı Çoklu Görev Servis Robotu ve Web Tabanlı Yer Kontrol İstasyonu</strong></p>

![ROS](https://img.shields.io/badge/ROS-Noetic-22314E?style=flat-square&logo=ros)
![Ubuntu](https://img.shields.io/badge/Ubuntu-20.04-E95420?style=flat-square&logo=ubuntu)
![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=flat-square&logo=python)
![Gazebo](https://img.shields.io/badge/Gazebo-Simulation-FF6600?style=flat-square)
![TurtleBot3](https://img.shields.io/badge/TurtleBot3-Waffle_Pi-00C0FF?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

</div>

---

<a name="türkçe"></a>

## 🇹🇷 Türkçe Bölüm

<details open>
<summary>📋 İçindekiler</summary>

- [Proje Hakkında](#proje-hakkında)
- [Özellikler](#özellikler)
- [Sistem Mimarisi](#sistem-mimarisi)
- [Gereksinimler](#gereksinimler)
- [Kurulum](#kurulum)
- [Kullanım](#kullanım)
- [Paket Yapısı](#paket-yapısı)
- [Web GCS Arayüzü](#web-gcs-arayüzü)
- [Geliştirici](#geliştirici)

</details>

---

### Proje Hakkında

Bu proje, **KTÜN Robotiğe Giriş Dersi** final ödevi kapsamında geliştirilmiştir. **AWS RoboMaker Bookstore World** simülasyon ortamında **TurtleBot3 Waffle Pi** robot platformu üzerinde çalışan tam otonom bir servis robotu sistemidir.

Robot; haritayı kendisi oluşturur, konumunu AMCL ile belirler, belirlenen 4 göreve noktasını sırayla ziyaret eder, her noktada QR kodu okuyup doğrular ve görev sonunda detaylı bir rapor oluşturur. Tüm süreç web tabanlı Yer Kontrol İstasyonu (GCS) üzerinden izlenip yönetilebilir.

---

### Özellikler

| Özellik | Açıklama |
|---|---|
| 🗺️ **SLAM Haritalama** | `gmapping` ile gerçek zamanlı harita oluşturma |
| 📍 **AMCL Lokalizasyon** | Otomatik başlangıç konumu tespiti, manuel pose gerekmez |
| 🧭 **Otonom Navigasyon** | `move_base` + DWA planlayıcı ile engel kaçınmalı rota |
| 📦 **Görev State Machine** | INIT→GO_TO→QR_VERIFY→REPORT→FINISH akışı |
| 📷 **QR Doğrulama** | `pyzbar` ile kamera görüntüsünden QR kod okuma |
| 🌐 **Web GCS** | Canlı kamera, hız kontrol, görev izleme, rapor popup |
| 💾 **Görev Raporu** | Süre, başarı/başarısız bilgilerini `.txt` olarak kaydeder |
| 🗺️ **GCS'den Harita Kaydetme** | Web arayüzünden tek tıkla `map_saver` tetikleme |

---

### Sistem Mimarisi

```
┌─────────────────────────────────────────────────────────┐
│                    Gazebo Simülasyon                     │
│   TurtleBot3 Waffle Pi  +  AWS Bookstore World          │
│   (LiDAR, Kamera, Odometri, QR Modelleri)               │
└────────────────────────┬────────────────────────────────┘
                         │ ROS Topics
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
  ┌──────────┐    ┌───────────┐    ┌────────────┐
  │   AMCL   │    │ move_base │    │  qr_reader │
  │(Lokalizas│    │(Navigasyon│    │  (pyzbar)  │
  └────┬─────┘    └─────┬─────┘    └─────┬──────┘
       │                │                │
       └────────────────▼────────────────┘
                        │
                ┌───────────────┐
                │ task_manager  │
                │ (State Machine│
                └───────┬───────┘
                        │ /task_manager/status
                        ▼
              ┌──────────────────┐
              │  rosbridge_server │ ws://localhost:9090
              └────────┬─────────┘
                       │
              ┌────────▼─────────┐
              │   Web GCS        │ http://localhost:8888
              │  (index.html)    │
              └──────────────────┘
```

---

### Gereksinimler

**İşletim Sistemi:** Ubuntu 20.04 LTS  
**ROS Dağıtımı:** ROS1 Noetic

```bash
# ROS Paketleri
sudo apt install ros-noetic-turtlebot3 \
                 ros-noetic-turtlebot3-simulations \
                 ros-noetic-navigation \
                 ros-noetic-map-server \
                 ros-noetic-amcl \
                 ros-noetic-move-base \
                 ros-noetic-rosbridge-server \
                 ros-noetic-web-video-server

# Python Kütüphaneleri
pip3 install pyzbar opencv-python

# libzbar sistem kütüphanesi
sudo apt install libzbar0

# AWS Bookstore World
# https://github.com/aws-robotics/aws-robomaker-bookstore-world
```

---

### Kurulum

```bash
# 1. Workspace oluştur
mkdir -p ~/service_robot/src
cd ~/service_robot/src

# 2. Repoyu klonla
git clone https://github.com/alprNer/bookstore_turtlebot_nav_gcs.git service_robot_mission

# 3. AWS Bookstore World'ü klonla (ayrı workspace'e)
mkdir -p ~/service_robot_ws/src && cd ~/service_robot_ws/src
git clone https://github.com/aws-robotics/aws-robomaker-bookstore-world.git

# 4. Her iki workspace'i derle
cd ~/service_robot_ws && catkin_make
cd ~/service_robot    && catkin_make

# 5. .bashrc'ye ekle (source sırası önemli!)
echo "source ~/service_robot_ws/devel/setup.bash" >> ~/.bashrc
echo "source ~/service_robot/devel/setup.bash"    >> ~/.bashrc
echo "export TURTLEBOT3_MODEL=waffle_pi"           >> ~/.bashrc
source ~/.bashrc
```

---

### Kullanım

#### Adım 1 — SLAM Haritalama

```bash
# Terminal 1
roslaunch service_robot_mission simulation.launch

# Terminal 2
roslaunch turtlebot3_slam turtlebot3_slam.launch slam_methods:=gmapping

# Terminal 3 — Teleop ile haritayı oluştur
roslaunch turtlebot3_teleop turtlebot3_teleop_key.launch

# Terminal 4 — Haritayı kaydet
rosrun map_server map_saver -f ~/service_robot/src/service_robot_mission/maps/map
```

> 💡 **İpucu:** GCS açıkken **"Haritayı Kaydet"** butonuyla da kaydedebilirsiniz.

#### Adım 2 — Otonom Görev

```bash
# Terminal 1 — Simülasyon
roslaunch service_robot_mission simulation.launch

# Terminal 2 — Navigasyon (otomatik lokalizasyon yapar)
roslaunch service_robot_mission navigation.launch

# Terminal 3 — Yer Kontrol İstasyonu
roslaunch service_robot_mission gcs.launch

# Terminal 4 — Görev Yöneticisi
roslaunch service_robot_mission task_manager.launch
```

**Tarayıcıda** `http://localhost:8888` → **🚀 GÖREV BAŞLAT** butonuna tıkla.

#### Görev Raporu

```bash
cat ~/gorev_raporlari/$(ls -t ~/gorev_raporlari/ | head -1)
```

---

### Paket Yapısı

```
service_robot_mission/
├── config/
│   └── mission.yaml          # Görev noktaları, koordinatlar, QR beklentileri
├── gcs/
│   ├── index.html            # Web GCS arayüzü (dark theme, animasyonlu)
│   └── roslib.min.js         # roslibjs kütüphanesi
├── launch/
│   ├── simulation.launch     # Gazebo + qradded.world
│   ├── navigation.launch     # AMCL + move_base + auto_localize
│   ├── task_manager.launch   # qr_reader + task_manager
│   └── gcs.launch            # rosbridge + web_video_server + GCS
├── maps/
│   ├── map.pgm               # SLAM harita görseli
│   └── map.yaml              # Harita konfigürasyonu
├── models/                   # Gazebo QR kod modelleri (4 adet)
│   ├── qr_danisma/
│   ├── qr_okuma/
│   ├── qr_roman/
│   └── qr_teknoloji/
└── src/
    ├── task_manager.py       # Görev state machine + zamanlama + rapor
    ├── qr_reader.py          # Kamera görüntüsünden QR okuma
    ├── auto_localize.py      # /initialpose ile otomatik AMCL lokalizasyon
    ├── map_saver_node.py     # GCS tetiklemeli harita kaydetme
    └── serve_gcs.py          # GCS için HTTP sunucusu
```

---

### Web GCS Arayüzü

| Bileşen | Açıklama |
|---|---|
| 📷 Canlı Kamera | `web_video_server` MJPEG akışı |
| 🎮 Hız Kontrol | Linear/Angular slider, W/A/S/D klavye |
| ⛔ Acil Dur | Anında `/cmd_vel` sıfırlama |
| 🚀 Görev Başlat | `/mission/start` ile task_manager tetikleme |
| 📋 Görev Kartları | DANIŞMA / OKUMA / ROMAN / TEKNOLOJİ durumları |
| 🖥️ Canlı Log | `/task_manager/status` ve `/rosout_agg` takibi |
| 🗺️ Harita Kaydet | Dönen animasyonlu buton, anlık geri bildirim |
| 🏆 Rapor Popup | Görev bitince istatistik + tam rapor metni |

---

### Geliştirici

<div align="center">

**Alperen ER**  
RACLAB — KTÜN Robotiğe Giriş Dersi Final Projesi

</div>

---

<a name="english"></a>

## 🇬🇧 English Section

<details>
<summary>📋 Table of Contents</summary>

- [About](#about)
- [Features](#features)
- [System Architecture](#system-architecture)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Package Structure](#package-structure)
- [Web GCS Interface](#web-gcs-interface)

</details>

---

### About

This project was developed as a final assignment for the **KTÜN Introduction to Robotics** course. It implements a fully autonomous service robot running on **TurtleBot3 Waffle Pi** inside the **AWS RoboMaker Bookstore World** simulation environment.

The robot autonomously builds a map, localizes itself via AMCL, navigates to 4 mission waypoints in sequence, reads and verifies QR codes at each location, and generates a detailed mission report. The entire process can be monitored and controlled through a web-based Ground Control Station (GCS).

---

### Features

| Feature | Description |
|---|---|
| 🗺️ **SLAM Mapping** | Real-time map building with `gmapping` |
| 📍 **AMCL Localization** | Automatic initial pose detection, no manual 2D estimate needed |
| 🧭 **Autonomous Navigation** | `move_base` + DWA planner with obstacle avoidance |
| 📦 **Mission State Machine** | INIT→GO_TO→QR_VERIFY→REPORT→FINISH flow |
| 📷 **QR Verification** | Camera-based QR code reading with `pyzbar` |
| 🌐 **Web GCS** | Live camera, velocity control, mission tracking, report popup |
| 💾 **Mission Report** | Saves timing, success/fail data as `.txt` file |
| 🗺️ **GCS Map Save** | One-click `map_saver` trigger from web interface |

---

### System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Gazebo Simulation                     │
│   TurtleBot3 Waffle Pi  +  AWS Bookstore World          │
│   (LiDAR, Camera, Odometry, QR Models)                  │
└────────────────────────┬────────────────────────────────┘
                         │ ROS Topics
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
  ┌──────────┐    ┌───────────┐    ┌────────────┐
  │   AMCL   │    │ move_base │    │  qr_reader │
  │(Localize)│    │(Navigation│    │  (pyzbar)  │
  └────┬─────┘    └─────┬─────┘    └─────┬──────┘
       └────────────────▼────────────────┘
                        │
                ┌───────────────┐
                │ task_manager  │
                │ (State Machine│
                └───────┬───────┘
                        │ /task_manager/status
              ┌─────────▼──────────┐
              │  rosbridge_server  │ ws://localhost:9090
              └────────┬───────────┘
              ┌────────▼─────────┐
              │   Web GCS        │ http://localhost:8888
              └──────────────────┘
```

---

### Requirements

**OS:** Ubuntu 20.04 LTS | **ROS:** Noetic

```bash
sudo apt install ros-noetic-turtlebot3 ros-noetic-navigation \
                 ros-noetic-rosbridge-server ros-noetic-web-video-server
pip3 install pyzbar opencv-python
sudo apt install libzbar0
```

---

### Installation

```bash
# 1. Create workspaces
mkdir -p ~/service_robot/src ~/service_robot_ws/src

# 2. Clone this repo
cd ~/service_robot/src
git clone https://github.com/alprNer/bookstore_turtlebot_nav_gcs.git service_robot_mission

# 3. Clone AWS Bookstore World
cd ~/service_robot_ws/src
git clone https://github.com/aws-robotics/aws-robomaker-bookstore-world.git

# 4. Build both workspaces
cd ~/service_robot_ws && catkin_make
cd ~/service_robot    && catkin_make

# 5. Add to .bashrc (source order matters!)
echo "source ~/service_robot_ws/devel/setup.bash" >> ~/.bashrc
echo "source ~/service_robot/devel/setup.bash"    >> ~/.bashrc
echo "export TURTLEBOT3_MODEL=waffle_pi"           >> ~/.bashrc
source ~/.bashrc
```

---

### Usage

#### Step 1 — SLAM Mapping

```bash
roslaunch service_robot_mission simulation.launch
roslaunch turtlebot3_slam turtlebot3_slam.launch slam_methods:=gmapping
roslaunch turtlebot3_teleop turtlebot3_teleop_key.launch
# Save map
rosrun map_server map_saver -f ~/service_robot/src/service_robot_mission/maps/map
```

#### Step 2 — Autonomous Mission

```bash
roslaunch service_robot_mission simulation.launch    # Terminal 1
roslaunch service_robot_mission navigation.launch    # Terminal 2
roslaunch service_robot_mission gcs.launch           # Terminal 3
roslaunch service_robot_mission task_manager.launch  # Terminal 4
```

Open `http://localhost:8888` → Click **🚀 START MISSION**

---

### Package Structure

```
service_robot_mission/
├── config/mission.yaml       # Waypoints, coordinates, QR expectations
├── gcs/index.html            # Web GCS (dark theme, animated)
├── launch/                   # simulation, navigation, gcs, task_manager
├── maps/                     # SLAM-generated map files
├── models/                   # Gazebo QR code models (x4)
└── src/
    ├── task_manager.py       # Mission state machine + timing + report
    ├── qr_reader.py          # Camera QR code reader
    ├── auto_localize.py      # Automatic AMCL localization
    ├── map_saver_node.py     # GCS-triggered map saving
    └── serve_gcs.py          # HTTP server for GCS
```

---

### Web GCS Interface

| Component | Description |
|---|---|
| 📷 Live Camera | `web_video_server` MJPEG stream |
| 🎮 Velocity Control | Linear/Angular sliders + W/A/S/D keyboard |
| ⛔ Emergency Stop | Instant `/cmd_vel` zero command |
| 🚀 Start Mission | Triggers `task_manager` via `/mission/start` |
| 📋 Task Cards | Live status for all 4 mission points |
| 🖥️ Live Log | `/task_manager/status` + `/rosout_agg` feed |
| 🗺️ Save Map | Animated button with instant feedback |
| 🏆 Report Popup | Stats + full report text on mission complete |

---

<div align="center">

**Alperen ER** — RACLAB  
*KTÜN Introduction to Robotics — Final Project*

</div>
