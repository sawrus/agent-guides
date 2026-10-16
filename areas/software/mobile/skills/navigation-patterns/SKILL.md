---
name: navigation-patterns
description: "Provides React Navigation architecture and deep link validation patterns; use when designing mobile app navigation, implementing deep linking, or handling auth flows."
---

# Skill: Navigation Patterns (React Navigation)

## When to load

When designing app navigation, implementing deep linking, or handling auth flows.

## Architecture

```typescript
const RootNavigator = () => {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) return <SplashScreen />;

  return (
    <NavigationContainer linking={linking} ref={navigationRef}>
      {isAuthenticated ? <AppNavigator /> : <AuthNavigator />}
    </NavigationContainer>
  );
};

const AppNavigator = () => (
  <BottomTabs.Navigator>
    <BottomTabs.Screen name="HomeTab" component={HomeStackNavigator} />
    <BottomTabs.Screen name="ProfileTab" component={ProfileStackNavigator} />
  </BottomTabs.Navigator>
);
```

## Deep Link Validation

```typescript
export const linking: LinkingOptions<RootStackParamList> = {
  prefixes: ['myapp://', 'https://myapp.com'],
  config: {
    screens: {
      HomeTab: {
        screens: {
          OrderDetail: {
            path: 'orders/:orderId',
            parse: { orderId: String },
            // Sanitize: only alphanumeric and dashes
            stringify: { orderId: (id) => id.replace(/[^a-zA-Z0-9-]/g, '') },
          },
        },
      },
    },
  },
};
```
