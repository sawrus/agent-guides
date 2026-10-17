---
name: native-modules
description: "Guides native module integration, including when to bridge native SDKs and biometric authentication; use when integrating device APIs, bridging to native SDKs, or debugging platform-specific behavior."
---

# Skill: Native Module Integration

## When to load

When integrating device APIs, bridging to native SDKs, or debugging platform-specific behavior.

## When to Use Native Modules

```
Use Native Module:
- Device hardware (camera, accelerometer, NFC, Bluetooth)
- Cryptographic operations (device secure enclave)
- Computation-intensive tasks (image processing, on-device ML)
- Third-party SDKs without JS wrapper

Stay in JS/React Native:
- UI rendering and interactions
- Network requests
- State management
- Business logic not requiring device APIs
```

## Biometric Authentication

```typescript
import ReactNativeBiometrics from 'react-native-biometrics';

export async function authenticateWithBiometrics(): Promise<boolean> {
  const rnBiometrics = new ReactNativeBiometrics({ allowDeviceCredentials: true });
  const { biometryType } = await rnBiometrics.isSensorAvailable();
  if (!biometryType) return authenticateWithPin();

  const { success } = await rnBiometrics.simplePrompt({
    promptMessage: biometryType === 'FaceID' ? 'Confirm with Face ID' : 'Confirm with fingerprint'
  });
  return success;
}
```
