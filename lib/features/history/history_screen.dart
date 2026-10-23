import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../../core/constants/app_colors.dart';
import '../../core/network/api_client.dart';
import '../../core/storage/local_storage.dart';
import '../../models/scan_result_model.dart';
import '../../services/auth_service.dart';
import '../../widgets/status_badge.dart';
import '../analysis/result_screen.dart';
import '../auth/login_screen.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => HistoryScreenState();
}

class HistoryScreenState extends State<HistoryScreen> with WidgetsBindingObserver {
  List<ScanResult> _history = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    loadHistory();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      loadHistory();
    }
  }

  Future<void> loadHistory() async {
    setState(() => _isLoading = true);
    final list = await LocalStorage.getCachedHistory();
    if (mounted) {
      setState(() {
        _history = list;
        _isLoading = false;
      });
    }
  }

  void _deleteItem(int index) async {
    await LocalStorage.deleteScanFromHistory(index);
    loadHistory();
  }

  void _clearAll() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: const Text("Clear History?", style: TextStyle(fontWeight: FontWeight.w700)),
        content: const Text("This will permanently remove all past scan records from your device."),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text("Cancel", style: TextStyle(color: AppColors.textSecondary)),
          ),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            style: FilledButton.styleFrom(backgroundColor: AppColors.statusAvoid),
            child: const Text("Clear All"),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      await LocalStorage.clearHistory();
      loadHistory();
    }
  }

  Future<void> _openRenameDialog(ScanResult item, int index) async {
    final controller = TextEditingController(text: item.displayName);
    String? errorMessage;

    final newName = await showDialog<String>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDialogState) {
          return AlertDialog(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
            title: const Text(
              "Give this product a name",
              style: TextStyle(fontWeight: FontWeight.w700, fontSize: 18),
            ),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                TextField(
                  controller: controller,
                  autofocus: true,
                  textCapitalization: TextCapitalization.sentences,
                  decoration: InputDecoration(
                    hintText: "e.g., My favourite biscuits",
                    errorText: errorMessage,
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                      borderSide: const BorderSide(color: AppColors.primary, width: 2),
                    ),
                  ),
                  onChanged: (_) {
                    if (errorMessage != null) {
                      setDialogState(() => errorMessage = null);
                    }
                  },
                ),
              ],
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(ctx).pop(null),
                child: const Text("Cancel", style: TextStyle(color: AppColors.textSecondary)),
              ),
              FilledButton(
                onPressed: () {
                  final trimmed = controller.text.trim();
                  if (trimmed.isEmpty) {
                    setDialogState(() {
                      errorMessage = "Please enter a product name";
                    });
                    return;
                  }
                  Navigator.of(ctx).pop(trimmed);
                },
                child: const Text("Save"),
              ),
            ],
          );
        },
      ),
    );

    if (newName != null && newName.trim().isNotEmpty) {
      final updated = item.copyWith(customProductName: newName.trim());
      setState(() {
        _history[index] = updated;
      });
      await LocalStorage.updateScanInHistory(updated);
      if (updated.scanId != null) {
        ApiClient().updateScanDecisionOrName(
          scanId: updated.scanId!,
          customProductName: newName.trim(),
        );
      }
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text("Product name updated successfully"),
            backgroundColor: AppColors.primaryDark,
            duration: Duration(seconds: 2),
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = Provider.of<AuthService>(context);

    // Show sign-in prompt for guest users
    if (!auth.isAuthenticated) {
      return Scaffold(
        backgroundColor: AppColors.background,
        appBar: AppBar(title: const Text('Scan History')),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 32),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Container(
                  width: 72,
                  height: 72,
                  decoration: BoxDecoration(
                    color: AppColors.primaryLight,
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(Icons.history_rounded,
                      color: AppColors.primaryDark, size: 36),
                ),
                const SizedBox(height: 20),
                const Text(
                  'Sign in to view history',
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w700,
                    color: AppColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Your scan history is saved to your account. Sign in to access it.',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 14,
                    color: AppColors.textSecondary,
                    height: 1.5,
                  ),
                ),
                const SizedBox(height: 28),
                SizedBox(
                  width: double.infinity,
                  height: 50,
                  child: FilledButton(
                    onPressed: () async {
                      await Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) =>
                              const LoginScreen(redirectAfterLogin: true),
                        ),
                      );
                      // Reload history after sign-in
                      loadHistory();
                    },
                    child: const Text(
                      'Sign In',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      );
    }

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Scan History'),
        actions: [
          if (_history.isNotEmpty)
            IconButton(
              icon: const Icon(Icons.delete_outline_rounded, color: AppColors.textSecondary),
              tooltip: 'Clear History',
              onPressed: _clearAll,
            ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _history.isEmpty
              ? _buildEmptyState()
              : RefreshIndicator(
                  onRefresh: loadHistory,
                  child: ListView.builder(
                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                    itemCount: _history.length,
                    itemBuilder: (context, index) {
                      final item = _history[index];
                      return Dismissible(
                        key: ValueKey('${item.displayName}_${item.createdAt.millisecondsSinceEpoch}_$index'),
                        direction: DismissDirection.endToStart,
                        background: Container(
                          alignment: Alignment.centerRight,
                          padding: const EdgeInsets.only(right: 20),
                          margin: const EdgeInsets.symmetric(vertical: 6),
                          decoration: BoxDecoration(
                            color: AppColors.statusAvoidBg,
                            borderRadius: BorderRadius.circular(16),
                          ),
                          child: const Icon(Icons.delete_rounded, color: AppColors.statusAvoid),
                        ),
                        onDismissed: (_) => _deleteItem(index),
                        child: _buildHistoryCard(item, index),
                      );
                    },
                  ),
                ),
    );
  }

  Widget _buildHistoryCard(ScanResult item, int index) {
    final dateTimeStr = DateFormat('MMM d, h:mm a').format(item.createdAt);
    final count = item.ingredients.length;
    final ingredientText = count == 1 ? "1 ingredient" : "$count ingredients";
    final categoryText = item.productCategory.isNotEmpty ? item.productCategory : "Food Product";
    final hasCustomName = item.customProductName != null && item.customProductName!.trim().isNotEmpty;

    return InkWell(
      onTap: () async {
        await Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => ResultScreen(result: item)),
        );
        loadHistory();
      },
      borderRadius: BorderRadius.circular(16),
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 6),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppColors.background,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppColors.border),
          boxShadow: [AppColors.cardShadow],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: item.statusBgColor,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  alignment: Alignment.center,
                  child: Text(
                    item.statusEmoji,
                    style: const TextStyle(fontSize: 20),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Primary name with double-tap gesture to rename
                      GestureDetector(
                        onDoubleTap: () => _openRenameDialog(item, index),
                        behavior: HitTestBehavior.opaque,
                        child: Row(
                          children: [
                            Flexible(
                              child: Text(
                                item.displayName,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                  fontSize: 15,
                                  fontWeight: FontWeight.w700,
                                  color: AppColors.textPrimary,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                      if (hasCustomName &&
                          item.productName.isNotEmpty &&
                          item.productName != item.displayName &&
                          item.productName != 'Scanned Product' &&
                          item.productName != 'Unknown Product') ...[
                        const SizedBox(height: 2),
                        Text(
                          "Original: ${item.productName}",
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            fontSize: 12,
                            color: AppColors.textTertiary,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                      const SizedBox(height: 3),
                      Text(
                        "$categoryText • $ingredientText",
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontSize: 12,
                          color: AppColors.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    StatusBadge(status: item.overallStatus),
                    const SizedBox(height: 6),
                    // Clear Edit / Pencil icon button
                    IconButton(
                      icon: const Icon(Icons.edit_outlined, size: 18, color: AppColors.textSecondary),
                      tooltip: 'Rename product',
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(),
                      onPressed: () => _openRenameDialog(item, index),
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 10),
            const Divider(height: 1, thickness: 0.5, color: AppColors.border),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  "Score: ${item.score}/100 • $dateTimeStr",
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textSecondary,
                  ),
                ),
                if (item.purchaseDecision == 'YES')
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2.5),
                    decoration: BoxDecoration(
                      color: AppColors.statusGoodBg,
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(
                        color: AppColors.statusGood.withValues(alpha: 0.4),
                      ),
                    ),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.check_circle_rounded, size: 12, color: AppColors.statusGood),
                        SizedBox(width: 4),
                        Text(
                          "Will Buy",
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
                            color: AppColors.statusGood,
                          ),
                        ),
                      ],
                    ),
                  )
                else if (item.purchaseDecision == 'NO')
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2.5),
                    decoration: BoxDecoration(
                      color: AppColors.statusAvoidBg,
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(
                        color: AppColors.statusAvoid.withValues(alpha: 0.4),
                      ),
                    ),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.cancel_rounded, size: 12, color: AppColors.statusAvoid),
                        SizedBox(width: 4),
                        Text(
                          "Won't Buy",
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
                            color: AppColors.statusAvoid,
                          ),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: const [
          Icon(Icons.history_rounded, size: 64, color: AppColors.textTertiary),
          SizedBox(height: 12),
          Text(
            "No scans yet",
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w700,
              color: AppColors.textPrimary,
            ),
          ),
          SizedBox(height: 4),
          Text(
            "Scanned ingredient labels will appear here.",
            style: TextStyle(
              fontSize: 14,
              color: AppColors.textSecondary,
            ),
          ),
        ],
      ),
    );
  }
}
