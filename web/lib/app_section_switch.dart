import 'package:flutter/material.dart';

enum AppSection { temperature, sleep }

class AppSectionTabs extends StatefulWidget implements PreferredSizeWidget {
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
  State<AppSectionTabs> createState() => _AppSectionTabsState();
}

class _AppSectionTabsState extends State<AppSectionTabs>
    with SingleTickerProviderStateMixin {
  late final TabController _controller;

  int _indexFor(AppSection section) =>
      section == AppSection.temperature ? 0 : 1;

  @override
  void initState() {
    super.initState();
    _controller = TabController(
      length: 2,
      vsync: this,
      initialIndex: _indexFor(widget.selected),
    );
  }

  @override
  void didUpdateWidget(AppSectionTabs oldWidget) {
    super.didUpdateWidget(oldWidget);
    final index = _indexFor(widget.selected);
    if (_controller.index != index) {
      _controller.index = index;
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return TabBar(
      controller: _controller,
      onTap: (index) => widget.onSelected(
        index == 0 ? AppSection.temperature : AppSection.sleep,
      ),
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
    );
  }
}
