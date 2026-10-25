import 'package:flutter/material.dart';

import 'api.dart';
import 'dashboard_page.dart';
import 'login_page.dart';

void main() {
  runApp(const JoanaApp());
}

class JoanaApp extends StatefulWidget {
  const JoanaApp({super.key});

  @override
  State<JoanaApp> createState() => _JoanaAppState();
}

class _JoanaAppState extends State<JoanaApp> {
  bool _loggedIn = Api.savedPassword != null;

  void _setLoggedIn(bool value) {
    if (!value) Api.logout();
    setState(() => _loggedIn = value);
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Quarto Jojo',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.indigo,
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
      ),
      home: _loggedIn
          ? DashboardPage(onLogout: () => _setLoggedIn(false))
          : LoginPage(onLoggedIn: () => _setLoggedIn(true)),
    );
  }
}
