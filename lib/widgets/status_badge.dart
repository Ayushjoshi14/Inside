import 'package:flutter/material.dart';
import '../core/constants/app_colors.dart';

class StatusBadge extends StatelessWidget {
  final String status; // 'GOOD', 'CAUTION', 'AVOID'
  final bool isLarge;

  const StatusBadge({
    super.key,
    required this.status,
    this.isLarge = false,
  });

  @override
  Widget build(BuildContext context) {
    Color bg;
    Color text;
    String label;
    IconData icon;

    switch (status.toUpperCase()) {
      case 'AVOID':
        bg = AppColors.statusAvoidBg;
        text = AppColors.statusAvoid;
        label = 'AVOID';
        icon = Icons.cancel_rounded;
        break;
      case 'CAUTION':
        bg = AppColors.statusCautionBg;
        text = AppColors.statusCaution;
        label = 'CHECK';
        icon = Icons.warning_amber_rounded;
        break;
      case 'GOOD':
      default:
        bg = AppColors.statusGoodBg;
        text = AppColors.statusGood;
        label = 'GOOD';
        icon = Icons.check_circle_rounded;
        break;
    }

    if (isLarge) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: bg,
          borderRadius: BorderRadius.circular(24),
          border: Border.all(color: text.withValues(alpha: 0.3), width: 1.5),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: text, size: 20),
            const SizedBox(width: 8),
            Text(
              label,
              style: TextStyle(
                color: text,
                fontWeight: FontWeight.w700,
                fontSize: 14,
                letterSpacing: 0.5,
              ),
            ),
          ],
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, color: text, size: 14),
          const SizedBox(width: 4),
          Text(
            label,
            style: TextStyle(
              color: text,
              fontWeight: FontWeight.w700,
              fontSize: 12,
            ),
          ),
        ],
      ),
    );
  }
}
