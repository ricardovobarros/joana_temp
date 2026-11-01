import 'package:flutter/material.dart';

import 'app_section_switch.dart';
import 'dashboard_page.dart';
import 'sleep_page.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  AppSection _section = AppSection.sleep;

  @override
  Widget build(BuildContext context) {
    return IndexedStack(
      index: _section == AppSection.sleep ? 0 : 1,
      children: [
        SleepPage(onSectionSelected: _selectSection),
        DashboardPage(onSectionSelected: _selectSection),
      ],
    );
  }

  void _selectSection(AppSection section) {
    if (section != _section) setState(() => _section = section);
  }
}
