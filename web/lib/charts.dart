import 'dart:math';

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import 'api.dart';

const _weekdays = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'];

class HourBucket {
  HourBucket(this.start, this.average);

  final DateTime start;
  final double? average;
}

class DayBucket {
  DayBucket(this.day, this.min, this.max);

  final DateTime day;
  final double? min;
  final double? max;
}

List<HourBucket> hourlyAverages(List<Reading> readings, DateTime now) {
  final currentHour = DateTime(now.year, now.month, now.day, now.hour);
  return List.generate(24, (i) {
    final start = currentHour.subtract(Duration(hours: 23 - i));
    final end = start.add(const Duration(hours: 1));
    final values = readings
        .where((r) => !r.at.isBefore(start) && r.at.isBefore(end))
        .map((r) => r.temperature)
        .toList();
    final average =
        values.isEmpty ? null : values.reduce((a, b) => a + b) / values.length;
    return HourBucket(start, average);
  });
}

List<DayBucket> dailyMinMax(List<Reading> readings, DateTime now) {
  return List.generate(7, (i) {
    final day = DateTime(now.year, now.month, now.day - (6 - i));
    final values = readings
        .where((r) =>
            r.at.year == day.year && r.at.month == day.month && r.at.day == day.day)
        .map((r) => r.temperature)
        .toList();
    if (values.isEmpty) return DayBucket(day, null, null);
    return DayBucket(day, values.reduce(min), values.reduce(max));
  });
}

(double, double) _yRange(Iterable<double> values) {
  if (values.isEmpty) return (0, 30);
  final low = (values.reduce(min) - 2).floorToDouble();
  final high = (values.reduce(max) + 2).ceilToDouble();
  return (low, high);
}

Widget _axisLabel(TitleMeta meta, String text) => SideTitleWidget(
      meta: meta,
      child: Text(text, style: const TextStyle(fontSize: 11)),
    );

FlTitlesData _titles(Widget Function(double, TitleMeta) bottom) => FlTitlesData(
      topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
      rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
      leftTitles: AxisTitles(
        sideTitles: SideTitles(
          showTitles: true,
          reservedSize: 36,
          getTitlesWidget: (value, meta) =>
              _axisLabel(meta, '${value.toStringAsFixed(0)}°'),
        ),
      ),
      bottomTitles: AxisTitles(
        sideTitles: SideTitles(
          showTitles: true,
          reservedSize: 28,
          getTitlesWidget: bottom,
        ),
      ),
    );

class HourlyTemperatureChart extends StatelessWidget {
  const HourlyTemperatureChart({super.key, required this.buckets});

  final List<HourBucket> buckets;

  @override
  Widget build(BuildContext context) {
    final color = Theme.of(context).colorScheme.primary;
    final (low, high) =
        _yRange(buckets.map((b) => b.average).whereType<double>());
    final hourFormat = DateFormat('ha');

    return BarChart(
      BarChartData(
        minY: low,
        maxY: high,
        gridData: const FlGridData(drawVerticalLine: false),
        borderData: FlBorderData(show: false),
        titlesData: _titles((value, meta) {
          final i = value.toInt();
          if (i % 3 != 0 || i >= buckets.length) return const SizedBox.shrink();
          return _axisLabel(meta, hourFormat.format(buckets[i].start));
        }),
        barTouchData: BarTouchData(
          touchTooltipData: BarTouchTooltipData(
            getTooltipItem: (group, groupIndex, rod, rodIndex) => BarTooltipItem(
              '${hourFormat.format(buckets[group.x].start)}\n'
              '${rod.toY.toStringAsFixed(1)} °C',
              const TextStyle(fontWeight: FontWeight.bold),
            ),
          ),
        ),
        barGroups: [
          for (var i = 0; i < buckets.length; i++)
            BarChartGroupData(
              x: i,
              barRods: buckets[i].average == null
                  ? []
                  : [
                      BarChartRodData(
                        fromY: low,
                        toY: buckets[i].average!,
                        color: color,
                        width: 10,
                        borderRadius: const BorderRadius.vertical(
                            top: Radius.circular(3)),
                      ),
                    ],
            ),
        ],
      ),
    );
  }
}

class DailyMinMaxChart extends StatelessWidget {
  const DailyMinMaxChart({super.key, required this.buckets});

  final List<DayBucket> buckets;

  @override
  Widget build(BuildContext context) {
    final values = buckets.expand((b) => [b.min, b.max]).whereType<double>();
    final (low, high) = _yRange(values);

    return BarChart(
      BarChartData(
        minY: low,
        maxY: high,
        gridData: const FlGridData(drawVerticalLine: false),
        borderData: FlBorderData(show: false),
        titlesData: _titles((value, meta) {
          final i = value.toInt();
          if (i >= buckets.length) return const SizedBox.shrink();
          final day = buckets[i].day;
          return _axisLabel(meta, '${_weekdays[day.weekday - 1]} ${day.day}');
        }),
        barTouchData: BarTouchData(
          touchTooltipData: BarTouchTooltipData(
            getTooltipItem: (group, groupIndex, rod, rodIndex) {
              final b = buckets[group.x];
              return BarTooltipItem(
                'Mín ${b.min!.toStringAsFixed(1)} °C\n'
                'Máx ${b.max!.toStringAsFixed(1)} °C',
                const TextStyle(fontWeight: FontWeight.bold),
              );
            },
          ),
        ),
        barGroups: [
          for (var i = 0; i < buckets.length; i++)
            BarChartGroupData(
              x: i,
              barRods: buckets[i].min == null
                  ? []
                  : [
                      BarChartRodData(
                        fromY: buckets[i].min!,
                        toY: max(buckets[i].max!, buckets[i].min! + 0.2),
                        width: 22,
                        gradient: const LinearGradient(
                          begin: Alignment.bottomCenter,
                          end: Alignment.topCenter,
                          colors: [Colors.lightBlueAccent, Colors.deepOrangeAccent],
                        ),
                        borderRadius: BorderRadius.circular(4),
                      ),
                    ],
            ),
        ],
      ),
    );
  }
}
