import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import 'api.dart';

const _maxTimer = Duration(hours: 12);

String formatHoursMinutes(Duration d) {
  final clamped = d > _maxTimer ? _maxTimer : d;
  final hours = clamped.inHours.toString().padLeft(2, '0');
  final minutes = (clamped.inMinutes % 60).toString().padLeft(2, '0');
  return '$hours:$minutes';
}

class TimerCard extends StatelessWidget {
  const TimerCard({
    super.key,
    required this.session,
    required this.now,
    required this.busy,
    required this.onToggle,
  });

  final TimerSession? session;
  final DateTime now;
  final bool busy;
  final ValueChanged<bool> onToggle;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final running = session?.running ?? false;

    String lastActivation = '—';
    Duration duration = Duration.zero;
    if (session != null) {
      final started = session!.startedAt;
      final sameDay = started.year == now.year &&
          started.month == now.month &&
          started.day == now.day;
      lastActivation =
          DateFormat(sameDay ? 'h:mm a' : 'd/M h:mm a').format(started);
      duration = running
          ? now.difference(started)
          : Duration(seconds: session!.durationSeconds ?? 0);
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Icon(running ? Icons.timer : Icons.timer_off_outlined,
                    color: running ? theme.colorScheme.primary : null),
                const SizedBox(width: 8),
                Text(running ? 'Timer ativo' : 'Timer desligado',
                    style: theme.textTheme.titleMedium),
              ],
            ),
            const SizedBox(height: 16),
            Text(
              formatHoursMinutes(duration),
              textAlign: TextAlign.center,
              style: theme.textTheme.displayMedium?.copyWith(
                fontFeatures: const [FontFeature.tabularFigures()],
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              '${running ? 'Ativado às' : 'Última ativação'}: $lastActivation',
              textAlign: TextAlign.center,
              style: theme.textTheme.bodyMedium,
            ),
            const SizedBox(height: 20),
            FilledButton.icon(
              onPressed: busy ? null : () => onToggle(!running),
              style: running
                  ? FilledButton.styleFrom(
                      backgroundColor: theme.colorScheme.error,
                      foregroundColor: theme.colorScheme.onError,
                    )
                  : null,
              icon: busy
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : Icon(running ? Icons.stop : Icons.play_arrow),
              label: Text(running ? 'Desativar timer' : 'Ativar timer'),
            ),
          ],
        ),
      ),
    );
  }
}
