import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:web/web.dart' as web;

const _apiBase = String.fromEnvironment('API_BASE');
const _storageKey = 'joana_password';

class ApiException implements Exception {
  ApiException(this.statusCode, this.message);

  final int statusCode;
  final String message;

  bool get unauthorized => statusCode == 401;

  @override
  String toString() => message;
}

class Reading {
  Reading(this.at, this.temperature, this.humidity);

  final DateTime at;
  final double temperature;
  final double? humidity;

  factory Reading.fromJson(Map<String, dynamic> json) => Reading(
        DateTime.parse(json['at'] as String).toLocal(),
        (json['t'] as num).toDouble(),
        (json['h'] as num?)?.toDouble(),
      );
}

class TimerSession {
  TimerSession(this.startedAt, this.endedAt, this.durationSeconds);

  final DateTime startedAt;
  final DateTime? endedAt;
  final int? durationSeconds;

  bool get running => endedAt == null;

  factory TimerSession.fromJson(Map<String, dynamic> json) => TimerSession(
        DateTime.parse(json['started_at'] as String).toLocal(),
        json['ended_at'] == null
            ? null
            : DateTime.parse(json['ended_at'] as String).toLocal(),
        json['duration_seconds'] as int?,
      );
}

class Dashboard {
  Dashboard(this.deviceOnline, this.readings, this.lastSession);

  final bool? deviceOnline;
  final List<Reading> readings;
  final TimerSession? lastSession;

  bool get timerRunning => lastSession?.running ?? false;

  factory Dashboard.fromJson(Map<String, dynamic> json) => Dashboard(
        json['device_online'] as bool?,
        (json['readings'] as List)
            .map((r) => Reading.fromJson(r as Map<String, dynamic>))
            .toList(),
        json['last_session'] == null
            ? null
            : TimerSession.fromJson(json['last_session'] as Map<String, dynamic>),
      );
}

class Api {
  static String? get savedPassword =>
      web.window.sessionStorage.getItem(_storageKey);

  static void logout() => web.window.sessionStorage.removeItem(_storageKey);

  static Uri _uri(String path) =>
      _apiBase.isEmpty ? Uri.base.resolve(path) : Uri.parse('$_apiBase$path');

  static Map<String, String> _headers() => {
        'Content-Type': 'application/json',
        'X-App-Password': savedPassword ?? '',
      };

  static Never _fail(http.Response response) {
    String message = 'Erro ${response.statusCode}';
    try {
      final detail = jsonDecode(response.body)['detail'];
      if (detail is String) message = detail;
    } catch (_) {}
    throw ApiException(response.statusCode, message);
  }

  static Future<void> login(String password) async {
    final response = await http.post(
      _uri('/api/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'password': password}),
    );
    if (response.statusCode != 200) _fail(response);
    web.window.sessionStorage.setItem(_storageKey, password);
  }

  static Future<Dashboard> dashboard() async {
    final response = await http.get(_uri('/api/dashboard'), headers: _headers());
    if (response.statusCode != 200) _fail(response);
    return Dashboard.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
  }

  static Future<void> setTimer(bool on) async {
    final response = await http.post(
      _uri('/api/timer'),
      headers: _headers(),
      body: jsonEncode({'action': on ? 'start' : 'stop'}),
    );
    if (response.statusCode != 200) _fail(response);
  }
}
