import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:inside/widgets/status_badge.dart';

void main() {
  testWidgets('StatusBadge renders GOOD status correctly', (WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: StatusBadge(status: 'GOOD'),
        ),
      ),
    );

    expect(find.text('GOOD'), findsOneWidget);
    expect(find.byIcon(Icons.check_circle_rounded), findsOneWidget);
  });

  testWidgets('StatusBadge renders AVOID status correctly', (WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: StatusBadge(status: 'AVOID'),
        ),
      ),
    );

    expect(find.text('AVOID'), findsOneWidget);
    expect(find.byIcon(Icons.cancel_rounded), findsOneWidget);
  });
}
