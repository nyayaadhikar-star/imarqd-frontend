import React from "react";
import { SafeAreaView, StatusBar, StyleSheet, Text, View } from "react-native";

export default function App() {
  return (
    <SafeAreaView style={styles.container}>
      <StatusBar />
      <View style={styles.card}>
        <Text style={styles.title}>Klyvo Mobile</Text>
        <Text>Expo + React Native scaffold</Text>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: "center", justifyContent: "center" },
  card: { padding: 24, borderRadius: 12, backgroundColor: "#f3f4f6" },
  title: { fontSize: 20, fontWeight: "600", marginBottom: 8 },
});


