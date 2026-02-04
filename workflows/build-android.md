---
description: Build and test Android app
---

# Build and Test Android App

This workflow builds the Flutter app for Android platform and runs it on an emulator.

## Prerequisites

- Android SDK installed
- Android emulator configured
- Flutter dependencies installed

## Steps

1. **Clean the project**
   ```bash
   flutter clean
   ```

2. **Get dependencies**
   ```bash
   flutter pub get
   ```

3. **Run code generation (if needed)**
   ```bash
   dart run build_runner build --delete-conflicting-outputs
   ```

4. **Analyze code for issues**
   ```bash
   flutter analyze
   ```

5. **Run unit tests**
   ```bash
   flutter test
   ```

6. **List available Android emulators**
   ```bash
   flutter emulators
   ```

7. **Launch Android emulator (if not running)**
   ```bash
   flutter emulators --launch <emulator_id>
   ```
   Replace `<emulator_id>` with the ID from step 6 (e.g., `Medium_Phone_API_35`)

8. **Build APK**
   ```bash
   flutter build apk --debug
   ```

9. **Run app on emulator**
   ```bash
   flutter run -d <device_id>
   ```
   Or simply:
   ```bash
   flutter run
   ```
   Flutter will automatically select the running emulator.

10. **Verify the app launches successfully**
    - Check the console output for errors
    - Interact with the app on the emulator
    - Test VPN connection functionality

## Troubleshooting

- If build fails, check `android/build.gradle` and `android/app/build.gradle` for configuration issues
- Ensure native Android code in `android/` directory is not corrupted
- Check that AmneziaWG native libraries in `native_libs/amneziawg_android_full` are properly linked