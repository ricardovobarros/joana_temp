import 'package:flutter/material.dart';

enum AppSection { temperature, sleep }

class AppSectionTabs extends StatelessWidget implements PreferredSizeWidget {
  const AppSectionTabs({
    super.key,
    required this.selected,
    required this.onSelected,
  });

  final AppSection selected;
  final ValueChanged<AppSection> onSelected;

  @override
  Size get preferredSize => const Size.fromHeight(48);

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      initialIndex: selected == AppSection.temperature ? 0 : 1,
      child: TabBar(
        onTap: (index) =>
            onSelected(index == 0 ? AppSection.temperature : AppSection.sleep),
        tabs: const [
          Tab(
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text('°C', style: TextStyle(fontWeight: FontWeight.w700)),
                SizedBox(width: 8),
                Text('Temperatura'),
              ],
            ),
          ),
          Tab(
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [Icon(Icons.bedtime), SizedBox(width: 8), Text('Sono')],
            ),
          ),
        ],
      ),
    );
  }
}
