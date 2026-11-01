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
      detail = 'Sem energia até às 8:00';
    } else if (running) {
      headline = fan.speed ?? 'Ligado';
      detail = fan.speed == null ? 'Velocidade desconhecida' : 'Ligado';
      color = theme.colorScheme.primary;
    } else {
      headline = 'Desligado';
      detail = fan.state == FanState.unknown
          ? 'A aguardar leitura'
          : 'Tomada com energia. O ventilador liga no botão dele';
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
            FilledButton.icon(
              onPressed: busy || !online
                  ? null
                  : () {
                      if (!running && !plugOff) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text(
                              'A tomada já tem energia. O ventilador só arranca no botão dele.',
                            ),
                          ),
                        );
                        return;
                      }
                      onSetPlug(!running);
                    },
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
                  : Icon(running ? Icons.power_settings_new : Icons.power),
              label: Text(running ? 'Desligar ventilador' : 'Ligar energia'),
            ),
            if (online && !plugOff && !running) ...[
              const SizedBox(height: 8),
              TextButton(
                onPressed: busy ? null : () => onSetPlug(false),
                child: const Text('Cortar energia'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
