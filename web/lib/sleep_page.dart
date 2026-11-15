import 'dart:async';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import 'api.dart';
import 'app_section_switch.dart';
import 'device_status.dart';

class SleepPage extends StatefulWidget {
  const SleepPage({
    super.key,
    required this.section,
    required this.onSectionSelected,
  });

  final AppSection section;
  final ValueChanged<AppSection> onSectionSelected;

  @override
  State<SleepPage> createState() => _SleepPageState();
}

class _SleepPageState extends State<SleepPage> {
  SleepDashboard? _data;
  String? _error;
  bool _busy = false;
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    _load();
    _refreshTimer = Timer.periodic(const Duration(seconds: 30), (_) => _load());
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final data = await Api.sleepDashboard();
      if (!mounted) return;
      setState(() {
        _data = data;
        _error = null;
      });
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } catch (_) {
      if (mounted) setState(() => _error = 'Sem ligação ao servidor');
    }
  }

  Future<void> _record(String kind) async {
    setState(() => _busy = true);
    try {
      await Api.setSleeping(kind == 'sleep');
      await _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Falhou: $e')));
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
        title: const Text('Sono da Jojo'),
        bottom: AppSectionTabs(
          selected: widget.section,
          onSelected: widget.onSectionSelected,
        ),
        actions: [
          if (data != null) DeviceStatus(online: data.deviceOnline),
          IconButton(
            tooltip: 'Atualizar',
            icon: const Icon(Icons.refresh),
            onPressed: _load,
          ),
        ],
      ),
      body: data == null
          ? Center(
              child: _error == null
                  ? const CircularProgressIndicator()
                  : Text(_error!),
            )
          : _content(data),
    );
  }

  Widget _content(SleepDashboard data) {
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Text(
                _error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    'Sono da Jojo',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Cada botão grava só o horário. Não precisa de um par.',
                  ),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      Expanded(
                        child: FilledButton.icon(
                          onPressed: _busy ? null : () => _record('sleep'),
                          icon: const Icon(Icons.bedtime),
                          label: const Text('Dormiu'),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: FilledButton.icon(
                          onPressed: _busy ? null : () => _record('wake'),
                          icon: const Icon(Icons.wb_sunny),
                          label: const Text('Acordou'),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(8, 16, 8, 8),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    child: Text(
                      'Registos · últimos 30 dias',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                  ),
                  const SizedBox(height: 8),
                  if (data.events.isEmpty)
                    const Padding(
                      padding: EdgeInsets.all(16),
                      child: Text('Ainda sem registos'),
                    )
                  else
                    for (final event in data.events) _SleepRow(event: event),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _SleepRow extends StatelessWidget {
  const _SleepRow({required this.event});

  final SleepEvent event;

  @override
  Widget build(BuildContext context) {
    final slept = event.slept;
    final color = slept
        ? Theme.of(context).colorScheme.primary
        : Theme.of(context).colorScheme.tertiary;
    return ListTile(
      leading: Icon(slept ? Icons.bedtime : Icons.wb_sunny, color: color),
      title: Text(slept ? 'Dormiu' : 'Acordou'),
      trailing: Text(
        DateFormat('d/M HH:mm').format(event.at),
        style: Theme.of(context).textTheme.titleMedium?.copyWith(
          fontFeatures: const [FontFeature.tabularFigures()],
        ),
      ),
    );
  }
}
