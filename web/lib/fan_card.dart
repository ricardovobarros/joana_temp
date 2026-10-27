import 'package:flutter/material.dart';

import 'api.dart';

class FanCard extends StatelessWidget {
  const FanCard({
    super.key,
    required this.fan,
    required this.busy,
    required this.onSetPlug,
  });

  final FanStatus? fan;
  final bool busy;
  final ValueChanged<bool> onSetPlug;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final fan = this.fan;
    final online = fan != null && fan.plugOnline;
    final plugOff = online && fan.plugOn == false;
    final running = online && !plugOff && fan.state == FanState.on;

    final String headline;
    final String detail;
    Color? color;
    if (!online) {
      headline = 'Offline';
      detail = 'Sem ligação à tomada';
      color = theme.disabledColor;
    } else if (plugOff) {
      headline = 'Desligado';
      detail = 'Tomada sem energia';
    } else if (running) {
      headline = fan.speed ?? 'Ligado';
      detail = fan.speed == null ? 'Velocidade desconhecida' : 'Ligado';
      color = theme.colorScheme.primary;
    } else {
      headline = 'Desligado';
      detail = fan.state == FanState.unknown ? 'A aguardar leitura' : 'Em espera';
    }
    final watts = fan?.watts;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text('🌀 Ventilador', style: theme.textTheme.titleMedium),
            const SizedBox(height: 16),
            Text(
              headline,
              textAlign: TextAlign.center,
              style: theme.textTheme.displaySmall
                  ?.copyWith(fontWeight: FontWeight.w600, color: color),
            ),
            const SizedBox(height: 8),
            Text(
              online && watts != null
                  ? '$detail · ${watts.toStringAsFixed(0)} W'
                  : detail,
              textAlign: TextAlign.center,
              style: theme.textTheme.bodyMedium,
            ),
            const SizedBox(height: 20),
            if (plugOff)
              OutlinedButton.icon(
                onPressed: busy ? null : () => onSetPlug(true),
                icon: const Icon(Icons.power),
                label: const Text('Religar tomada'),
              )
            else
              FilledButton.icon(
                onPressed: busy || !running ? null : () => onSetPlug(false),
                style: FilledButton.styleFrom(
                  backgroundColor: theme.colorScheme.error,
                  foregroundColor: theme.colorScheme.onError,
                ),
                icon: busy
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.power_settings_new),
                label: const Text('Desligar ventilador'),
              ),
          ],
        ),
      ),
    );
  }
}
