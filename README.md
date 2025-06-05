# RTK-VL Robot Project

A comprehensive robotics platform integrating Dynamixel servos, LiDAR sensors, Neural Processing Unit (NPU), and camera systems for advanced vision and navigation capabilities.

## 🤖 System Overview

This project implements a modular robotics platform featuring:
- **Dynamixel Servos**: Precision motor control for robot locomotion
- **LiDAR**: Distance sensing and environmental mapping
- **NPU**: Neural processing for AI/ML computations
- **Cameras**: Computer vision and visual perception

## 📁 Project Structure

```
RTK-VL-robot/
├── src/                          # Main source code
│   ├── core/                     # Core system components
│   ├── hardware/                 # Hardware interface modules
│   ├── vision/                   # Computer vision processing
│   ├── navigation/               # Path planning and SLAM
│   ├── ai/                       # Neural network models
│   └── utils/                    # Utility functions
├── config/                       # Configuration files
├── data/                         # Data storage and logs
├── tests/                        # Unit and integration tests
├── scripts/                      # Utility scripts and tools
├── docs/                         # Documentation
├── models/                       # Pre-trained AI models
└── requirements.txt              # Python dependencies
```

## 🚀 Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Hardware**
   ```bash
   python scripts/setup_hardware.py
   ```

3. **Run System**
   ```bash
   python src/main.py
   ```

## 🔧 Hardware Components

- **Dynamixel Servos**: AX/MX/XM series compatibility
- **LiDAR**: RPLiDAR A1/A2/A3 support
- **NPU**: Compatible with Coral Edge TPU, Jetson Nano/Xavier
- **Cameras**: USB/CSI camera support with OpenCV

## 📖 Documentation

Detailed documentation is available in the `docs/` directory covering:
- Hardware setup and calibration
- Software architecture
- API reference
- Troubleshooting guide

## 🤝 Contributing

Please read our contributing guidelines in `docs/CONTRIBUTING.md` before submitting pull requests.

## 📄 License

This project is licensed under the terms specified in the LICENSE file. 