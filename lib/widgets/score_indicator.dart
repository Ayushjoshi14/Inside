import 'package:flutter/material.dart';
import '../core/constants/app_colors.dart';

class ScoreIndicator extends StatelessWidget {
  final int score;
  final String status;

  const ScoreIndicator({
    super.key,
    required this.score,
    required this.status,
  });

  Color get scoreColor {
    switch (status.toUpperCase()) {
      case 'AVOID':
        return AppColors.statusAvoid;
      case 'CAUTION':
        return AppColors.statusCaution;
      case 'GOOD':
      default:
        return AppColors.statusGood;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        Text(
          'Overall Score',
          style: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w500,
            color: AppColors.textSecondary,
          ),
        ),
        const SizedBox(height: 6),
        Row(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.baseline,
          textBaseline: TextBaseline.alphabetic,
          children: [
            Text(
              '$score',
              style: TextStyle(
                fontSize: 48,
                fontWeight: FontWeight.w800,
                color: scoreColor,
                letterSpacing: -1,
              ),
            ),
            const SizedBox(width: 4),
            Text(
              '/ 100',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.w600,
                color: AppColors.textTertiary,
              ),
            ),
          ],
        ),
      ],
    );
  }
}
