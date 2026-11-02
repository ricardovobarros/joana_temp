import 'package:flutter/material.dart';

class DeviceStatus extends StatelessWidget {
  const DeviceStatus({super.key, required this.online});

  final bool? online;

  @override
  Widget build(BuildContext context) {
    final (label, color) = switch (online) {
      true => ('ESP32 online', Colors.greenAccent),
      false => ('ESP32 offline', Colors.redAccent),
      null => ('ESP32 ?', Colors.grey),
    };
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8),
      child: Chip(
        avatar: Icon(Icons.circle, size: 12, color: color),
        label: Text(label),
      ),
    );
  }
}
