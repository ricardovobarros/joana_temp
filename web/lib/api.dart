import 'dart:convert';

import 'package:http/http.dart' as http;

const _apiBase = String.fromEnvironment('API_BASE');

class ApiException implements Exception {
  ApiException(this.statusCode, this.message);

  final int statusCode;
  final String message;

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

class SleepSession {
  SleepSession(this.startedAt, this.endedAt, this.durationSeconds);

  final DateTime startedAt;
  final DateTime? endedAt;
  final int? durationSeconds;

  bool get running => endedAt == null;

  factory SleepSession.fromJson(Map<String, dynamic> json) => SleepSession(
    DateTime.parse(json['started_at'] as String).toLocal(),
    json['ended_at'] == null
        ? null
        : DateTime.parse(json['ended_at'] as String).toLocal(),
    json['duration_seconds'] as int?,
  );
}

class SleepDashboard {
  SleepDashboard(this.sleeping, this.lastSession, this.sessions);

  final bool sleeping;
  final SleepSession? lastSession;
  final List<SleepSession> sessions;

  factory SleepDashboard.fromJson(Map<String, dynamic> json) => SleepDashboard(
    json['sleeping'] as bool? ?? false,
    json['last_session'] == null
        ? null
        : SleepSession.fromJson(json['last_session'] as Map<String, dynamic>),
    (json['sessions'] as List? ?? const [])
        .map((s) => SleepSession.fromJson(s as Map<String, dynamic>))
        .toList(),
  );
}

enum FanState { off, on, unknown }

class FanStatus {
  FanStatus(this.plugOnline, this.plugOn, this.watts, this.state, this.speed);

  final bool plugOnline;
  final bool? plugOn;
  final double? watts;
  final FanState state;
  final String? speed;

  factory FanStatus.fromJson(Map<String, dynamic> json) => FanStatus(
    json['plug_online'] as bool? ?? false,
    json['plug_on'] as bool?,
    (json['watts'] as num?)?.toDouble(),
    FanState.values.asNameMap()[json['state']] ?? FanState.unknown,
    json['speed'] as String?,
  );
}

class Dashboard {
  Dashboard(this.deviceOnline, this.readings, this.lastSession, this.fan);

  final bool? deviceOnline;
  final List<Reading> readings;
  final TimerSession? lastSession;
  final FanStatus? fan;

  bool get timerRunning => lastSession?.running ?? false;

  factory Dashboard.fromJson(Map<String, dynamic> json) => Dashboard(
    json['device_online'] as bool?,
    (json['readings'] as List)
        .map((r) => Reading.fromJson(r as Map<String, dynamic>))
        .toList(),
    json['last_session'] == null
        ? null
        : TimerSession.fromJson(json['last_session'] as Map<String, dynamic>),
    json['fan'] == null
        ? null
        : FanStatus.fromJson(json['fan'] as Map<String, dynamic>),
  );
}

class Api {
  static Uri _uri(String path) =>
      _apiBase.isEmpty ? Uri.base.resolve(path) : Uri.parse('$_apiBase$path');

  static Never _fail(http.Response response) {
    String message = 'Erro ${response.statusCode}';
    try {
      final detail = jsonDecode(response.body)['detail'];
      if (detail is String) message = detail;
    } catch (_) {}
    throw ApiException(response.statusCode, message);
  }

  static Future<Dashboard> dashboard() async {
    final response = await http.get(_uri('/api/dashboard'));
    if (response.statusCode != 200) _fail(response);
    return Dashboard.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }

  static Future<SleepDashboard> sleepDashboard() async {
    final response = await http.get(_uri('/api/sleep'));
    if (response.statusCode != 200) _fail(response);
    return SleepDashboard.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }

  static Future<void> setTimer(bool on) async {
    final response = await http.post(
      _uri('/api/timer'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'action': on ? 'start' : 'stop'}),
    );
    if (response.statusCode != 200) _fail(response);
  }

  /// `plugOn: false` desliga o ventilador; `true` só volta a dar energia à tomada.
  static Future<void> setFanPlug(bool plugOn) async {
    final response = await http.post(
      _uri('/api/fan'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'action': plugOn ? 'plug_on' : 'off'}),
    );
    if (response.statusCode != 200) _fail(response);
  }
}
