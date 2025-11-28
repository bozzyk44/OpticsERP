/** @odoo-module **/
/**
 * Refund Saga Pattern - Frontend Refund Blocking
 *
 * Author: AI Agent
 * Created: 2025-11-27
 * Task: OPTERP-47
 * Reference: CLAUDE.md §5 (Saga pattern), §7 (KKT adapter)
 *
 * Purpose:
 * Implement Saga pattern for refund blocking in POS UI.
 * Prevents refund if original receipt not synced to OFD.
 *
 * Flow:
 * 1. User initiates refund in POS
 * 2. Check original order fiscal_doc_id
 * 3. Call API: POST /pos/kkt/check_refund
 * 4. If blocked (HTTP 409) → Show error, prevent refund
 * 5. If allowed (HTTP 200) → Proceed with refund
 */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";

/**
 * Patch PosStore to add refund validation
 */
patch(PosStore.prototype, {
    /**
     * Check if refund is allowed (Saga pattern)
     *
     * @param {Object} originalOrder - Original order to refund
     * @returns {Promise<Boolean>} - True if refund allowed, false if blocked
     */
    async checkRefundAllowed(originalOrder) {
        // Get fiscal document ID from original order
        const fiscalDocId = originalOrder.fiscal_doc_id;

        if (!fiscalDocId) {
            // No fiscal document ID - allow refund (non-fiscal order or old order)
            console.log('[RefundSaga] No fiscal_doc_id found, allowing refund');
            return true;
        }

        try {
            console.log(`[RefundSaga] Checking refund allowed for fiscal_doc_id: ${fiscalDocId}`);

            // Call API to check refund allowed
            const result = await this.env.services.rpc({
                route: '/pos/kkt/check_refund',
                params: {
                    original_fiscal_doc_id: fiscalDocId,
                },
            });

            if (result.allowed) {
                console.log('[RefundSaga] Refund allowed (original synced)');
                return true;
            } else {
                // Refund blocked
                console.warn(`[RefundSaga] Refund blocked: ${result.reason}`);

                // Show error popup
                await this.env.services.popup.add(ErrorPopup, {
                    title: 'Refund Blocked',
                    body: this._getRefundBlockedMessage(result),
                });

                return false;
            }

        } catch (error) {
            console.error('[RefundSaga] Error checking refund:', error);

            // On error, show warning and allow refund (fail-open for UX)
            // Alternative: fail-closed (block refund on error) for strict compliance
            await this.env.services.popup.add(ErrorPopup, {
                title: 'Refund Check Failed',
                body: `Could not verify original receipt sync status.\n\nError: ${error.message || 'Unknown error'}\n\nProceeding with refund (manual verification required).`,
            });

            // Fail-open: Allow refund
            return true;

            // Fail-closed: Block refund
            // return false;
        }
    },

    /**
     * Get refund blocked message
     *
     * @param {Object} result - API result
     * @returns {String} - Formatted error message
     */
    _getRefundBlockedMessage(result) {
        const syncStatus = result.sync_status || 'unknown';
        const reason = result.reason || 'Original receipt not synced to OFD';

        let message = `${reason}\n\n`;

        if (syncStatus === 'pending') {
            message += `Sync Status: Pending (in offline buffer)\n\n`;
            message += `The original receipt has not been synced to the OFD yet.\n`;
            message += `Please wait for the offline buffer to sync before processing this refund.\n\n`;
            message += `You can check the buffer status in the offline indicator (top-right corner).`;
        } else if (syncStatus === 'unknown') {
            message += `Sync Status: Unknown\n\n`;
            message += `Could not determine the sync status of the original receipt.\n`;
            message += `Please contact support if this issue persists.`;
        } else {
            message += `Sync Status: ${syncStatus}\n\n`;
            message += `Please resolve the sync issue before processing this refund.`;
        }

        return message;
    },
});

/**
 * Override refund method to add Saga validation
 *
 * Note: This is a simplified implementation.
 * Real implementation depends on Odoo POS refund workflow.
 */
patch(PosStore.prototype, {
    /**
     * Create refund order (with Saga validation)
     *
     * @param {Object} originalOrder - Original order to refund
     * @returns {Promise<Object>} - Refund order
     */
    async createRefundOrder(originalOrder) {
        // Check if refund allowed (Saga pattern)
        const refundAllowed = await this.checkRefundAllowed(originalOrder);

        if (!refundAllowed) {
            // Refund blocked - do not proceed
            console.warn('[RefundSaga] Refund blocked, aborting');
            return null;
        }

        // Refund allowed - proceed with normal flow
        console.log('[RefundSaga] Refund allowed, proceeding');

        // Call original method (if exists)
        // This is a placeholder - real implementation depends on POS refund logic
        // return this._super(...arguments);

        // For now, return null (to be implemented when POS refund flow is known)
        console.warn('[RefundSaga] createRefundOrder not fully implemented yet');
        return null;
    },
});

export default PosStore;
