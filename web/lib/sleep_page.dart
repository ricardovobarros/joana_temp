import 'dart:async';
import 'dart:math';

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import 'api.dart';

const _dayStartHour = 18;
const _weekdays = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'];

class SleepPage extends StatefulWidget {
  const SleepPage({super.key});

  @override
  State<SleepPage> createState() => _SleepPageState();
}

class _SleepPageState extends State<SleepPage> {
  SleepDashboard? _data;
  String? _error;
  DateTime _now = DateTime.now();
  Timer? _refreshTimer;
  Timer? _clockTimer;

  @override
  void initState() {
    super.initState();
    _load();
    _refreshTimer = Timer.periodic(const Duration(seconds: 30), (_) => _load());
    _clockTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() => _now = DateTime.now());
    });
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    _clockTimer?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final data = await Api.sleepDashboard();
      if (!mounted) return;
      setState(() {
        _data = data;
        _error = null;
        _now = DateTime.now();
      });
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } catch (_) {
      if (mounted) setState(() => _error = 'Sem ligação ao servidor');
    }
  }

  @override
  Widget build(BuildContext context) {
    final data = _data;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Sono do bebé'),
        actions: [
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
    final boundary = _sleepDayStart(_now);
    final total = _totalSince(data.sessions, boundary, _now);
    final buckets = _sleepBuckets(data.sessions, _now);

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
          LayoutBuilder(
            builder: (context, constraints) {
              final status = _StatusCard(data: data, now: _now);
              final totalCard = _TotalCard(total: total, since: boundary);
              return constraints.maxWidth >= 650
                  ? IntrinsicHeight(
                      child: Row(
                        children: [
                          Expanded(child: status),
                          const SizedBox(width: 16),
                          Expanded(child: totalCard),
                        ],
                      ),
                    )
                  : Column(
                      children: [status, const SizedBox(height: 16), totalCard],
                    );
            },
          ),
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 20, 12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Períodos de sono · últimos 7 dias',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const Text(
                    'Cada barra é um período. Toque para ver os horários.',
                  ),
                  const SizedBox(height: 16),
                  SizedBox(height: 310, child: _SleepChart(buckets: buckets)),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _StatusCard extends StatelessWidget {
  const _StatusCard({required this.data, required this.now});
  final SleepDashboard data;
  final DateTime now;

  @override
  Widget build(BuildContext context) {
    final last = data.lastSession;
    final lastAt = last == null ? null : (last.endedAt ?? last.startedAt);
    final elapsed = data.sleeping && last != null
        ? now.difference(last.startedAt)
        : Duration.zero;
    final isToday =
        lastAt != null &&
        lastAt.year == now.year &&
        lastAt.month == now.month &&
        lastAt.day == now.day;
    final lastLabel = lastAt == null
        ? 'Ainda sem registos'
        : '${last!.endedAt == null ? 'Dormiu' : 'Acordou'} '
              '${isToday ? 'às' : 'em'} '
              '${DateFormat(isToday ? 'HH:mm' : 'd/M às HH:mm').format(lastAt)}';
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              data.sleeping ? '😴 Bebé dormindo' : '👶 Bebé acordado',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 12),
            Text(
              data.sleeping ? _formatDuration(elapsed) : '00:00:00',
              style: Theme.of(context).textTheme.displaySmall?.copyWith(
                fontFeatures: const [FontFeature.tabularFigures()],
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 8),
            Text(lastLabel, textAlign: TextAlign.center),
          ],
        ),
      ),
    );
  }
}

class _TotalCard extends StatelessWidget {
  const _TotalCard({required this.total, required this.since});
  final Duration total;
  final DateTime since;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            'Sono desde as 18:00',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 12),
          Text(
            _formatHoursMinutes(total),
            style: Theme.of(
              context,
            ).textTheme.displaySmall?.copyWith(fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 8),
          Text('Contagem desde ${DateFormat('d/M HH:mm').format(since)}'),
        ],
      ),
    ),
  );
}

class _SleepSegment {
  _SleepSegment(this.start, this.end, this.fromHour, this.toHour);
  final DateTime start;
  final DateTime end;
  final double fromHour;
  final double toHour;
}

class _SleepBucket {
  _SleepBucket(this.day, this.segments);
  final DateTime day;
  final List<_SleepSegment> segments;
}

DateTime _sleepDayStart(DateTime value) {
  final today = DateTime(value.year, value.month, value.day, _dayStartHour);
  return value.isBefore(today)
      ? today.subtract(const Duration(days: 1))
      : today;
}

List<_SleepBucket> _sleepBuckets(List<SleepSession> sessions, DateTime now) {
  final newest = _sleepDayStart(now);
  return List.generate(7, (index) {
    final day = newest.subtract(Duration(days: 6 - index));
    final endOfDay = day.add(const Duration(days: 1));
    final segments = <_SleepSegment>[];
    for (final session in sessions) {
      final end = session.endedAt ?? now;
      final clippedStart = session.startedAt.isAfter(day)
          ? session.startedAt
          : day;
      final clippedEnd = end.isBefore(endOfDay) ? end : endOfDay;
      if (clippedEnd.isAfter(clippedStart)) {
        segments.add(
          _SleepSegment(
            clippedStart,
            clippedEnd,
            clippedStart.difference(day).inSeconds / 3600,
            clippedEnd.difference(day).inSeconds / 3600,
          ),
        );
      }
    }
    return _SleepBucket(day, segments);
  });
}

Duration _totalSince(
  List<SleepSession> sessions,
  DateTime since,
  DateTime now,
) {
  var seconds = 0;
  for (final session in sessions) {
    final end = session.endedAt ?? now;
    final start = session.startedAt.isAfter(since) ? session.startedAt : since;
    if (end.isAfter(start)) seconds += end.difference(start).inSeconds;
  }
  return Duration(seconds: seconds);
}

String _formatDuration(Duration value) {
  final hours = value.inHours.toString().padLeft(2, '0');
  final minutes = (value.inMinutes % 60).toString().padLeft(2, '0');
  final seconds = (value.inSeconds % 60).toString().padLeft(2, '0');
  return '$hours:$minutes:$seconds';
}

String _formatHoursMinutes(Duration value) =>
    '${value.inHours}h ${(value.inMinutes % 60).toString().padLeft(2, '0')}min';

class _SleepChart extends StatelessWidget {
  const _SleepChart({required this.buckets});
  final List<_SleepBucket> buckets;

  @override
  Widget build(BuildContext context) {
    final color = Theme.of(context).colorScheme.primary;
    return BarChart(
      BarChartData(
        minY: 0,
        maxY: 24,
        alignment: BarChartAlignment.spaceAround,
        gridData: FlGridData(
          drawVerticalLine: false,
          horizontalInterval: 3,
          getDrawingHorizontalLine: (value) => FlLine(
            color: Theme.of(context).dividerColor.withValues(alpha: 0.35),
            strokeWidth: 1,
          ),
        ),
        borderData: FlBorderData(show: false),
        titlesData: FlTitlesData(
          topTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          rightTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 44,
              interval: 3,
              getTitlesWidget: (value, meta) {
                final hour = (_dayStartHour + value.toInt()) % 24;
                return SideTitleWidget(
                  meta: meta,
                  child: Text(
                    '${hour.toString().padLeft(2, '0')}:00',
                    style: const TextStyle(fontSize: 10),
                  ),
                );
              },
            ),
          ),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 42,
              getTitlesWidget: (value, meta) {
                final i = value.toInt();
                if (i < 0 || i >= buckets.length) {
                  return const SizedBox.shrink();
                }
                final day = buckets[i].day;
                return SideTitleWidget(
                  meta: meta,
                  child: Text(
                    '${_weekdays[day.weekday - 1]}\n${day.day}/${day.month}',
                    textAlign: TextAlign.center,
                    style: const TextStyle(fontSize: 10),
                  ),
                );
              },
            ),
          ),
        ),
        barTouchData: BarTouchData(
          touchTooltipData: BarTouchTooltipData(
            getTooltipItem: (group, groupIndex, rod, rodIndex) {
              final segment = buckets[group.x].segments[rodIndex];
              return BarTooltipItem(
                '${DateFormat('HH:mm').format(segment.start)} → '
                '${DateFormat('HH:mm').format(segment.end)}\n'
                '${_formatHoursMinutes(segment.end.difference(segment.start))}',
                const TextStyle(fontWeight: FontWeight.bold),
              );
            },
          ),
        ),
        barGroups: [
          for (var i = 0; i < buckets.length; i++)
            BarChartGroupData(
              x: i,
              groupVertically: true,
              barRods: [
                for (final segment in buckets[i].segments)
                  BarChartRodData(
                    fromY: segment.fromHour,
                    toY: max(segment.toHour, segment.fromHour + 0.04),
                    width: 22,
                    color: color,
                    borderRadius: BorderRadius.circular(4),
                  ),
              ],
            ),
        ],
      ),
    );
  }
}
