import 'dart:async';

import 'package:flutter/material.dart';

import 'api.dart';
import 'charts.dart';
import 'timer_card.dart';

class DashboardPage extends StatefulWidget {
  const DashboardPage({super.key, required this.onLogout});

  final VoidCallback onLogout;

  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  Dashboard? _data;
  String? _error;
  bool _busy = false;
  DateTime _now = DateTime.now();
  Timer? _refreshTimer;
  Timer? _clockTimer;

  @override
  void initState() {
    super.initState();
    _load();
    _refreshTimer =
        Timer.periodic(const Duration(seconds: 30), (_) => _load());
    _clockTimer = Timer.periodic(
        const Duration(seconds: 10), (_) => setState(() => _now = DateTime.now()));
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    _clockTimer?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final data = await Api.dashboard();
      if (!mounted) return;
      setState(() {
        _data = data;
        _error = null;
        _now = DateTime.now();
      });
    } on ApiException catch (e) {
      if (e.unauthorized) {
        widget.onLogout();
        return;
      }
      if (mounted) setState(() => _error = e.message);
    } catch (_) {
      if (mounted) setState(() => _error = 'Sem ligação ao servidor');
    }
  }

  Future<void> _toggleTimer(bool on) async {
    setState(() => _busy = true);
    try {
      await Api.setTimer(on);
      // Dá tempo ao ESP32 para executar e ao backend para gravar
      await Future.delayed(const Duration(seconds: 2));
      await _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('Falhou: $e')));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final data = _data;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Quarto Jojo'),
        actions: [
          if (data != null) _DeviceStatus(online: data.deviceOnline),
          IconButton(
            tooltip: 'Atualizar',
            icon: const Icon(Icons.refresh),
            onPressed: _load,
          ),
          IconButton(
            tooltip: 'Sair',
            icon: const Icon(Icons.logout),
            onPressed: widget.onLogout,
          ),
        ],
      ),
      body: data == null
          ? Center(
              child: _error == null
                  ? const CircularProgressIndicator()
                  : Text(_error!),
            )
          : _buildContent(data),
    );
  }

  Widget _buildContent(Dashboard data) {
    final timerCard = TimerCard(
      session: data.lastSession,
      now: _now,
      busy: _busy,
      onToggle: _toggleTimer,
    );
    final charts = Column(
      children: [
        _ChartCard(
          title: 'Temperatura - últimas 24 horas',
          subtitle: _latestReadingText(data),
          child: HourlyTemperatureChart(
              buckets: hourlyAverages(data.readings, _now)),
        ),
        const SizedBox(height: 16),
        _ChartCard(
          title: 'Mínima e máxima - últimos 7 dias',
          child: DailyMinMaxChart(buckets: dailyMinMax(data.readings, _now)),
        ),
      ],
    );

    return LayoutBuilder(builder: (context, constraints) {
      final wide = constraints.maxWidth >= 900;
      return SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Text(_error!,
                    style: TextStyle(color: Theme.of(context).colorScheme.error)),
              ),
            if (wide)
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(child: charts),
                  const SizedBox(width: 16),
                  SizedBox(width: 300, child: timerCard),
                ],
              )
            else ...[
              timerCard,
              const SizedBox(height: 16),
              charts,
            ],
          ],
        ),
      );
    });
  }

  String? _latestReadingText(Dashboard data) {
    if (data.readings.isEmpty) return 'Ainda sem leituras';
    final last = data.readings.last;
    final humidity =
        last.humidity == null ? '' : ' · ${last.humidity!.toStringAsFixed(0)}% hum.';
    return 'Agora: ${last.temperature.toStringAsFixed(1)} °C$humidity';
  }
}

class _ChartCard extends StatelessWidget {
  const _ChartCard({required this.title, this.subtitle, required this.child});

  final String title;
  final String? subtitle;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 16, 20, 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: theme.textTheme.titleMedium),
            if (subtitle != null)
              Text(subtitle!, style: theme.textTheme.bodySmall),
            const SizedBox(height: 16),
            SizedBox(height: 240, child: child),
          ],
        ),
      ),
    );
  }
}

class _DeviceStatus extends StatelessWidget {
  const _DeviceStatus({required this.online});

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
