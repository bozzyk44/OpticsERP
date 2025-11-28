/** @odoo-module **/
/**
 * Offline Indicator Widget - POS UI Component
 *
 * Author: AI Agent
 * Created: 2025-11-27
 * Task: OPTERP-45
 * Reference: CLAUDE.md §3.2 (optics_pos_ru54fz module)
 *
 * Purpose:
 * Displays offline buffer status and circuit breaker state in POS UI.
 * Updates every 30 seconds with color coding (green/yellow/red).
 *
 * Color Coding:
 * - GREEN: Online, buffer <50%, CB CLOSED
 * - YELLOW: Online, buffer 50-80%, CB HALF_OPEN
 * - RED: Offline, buffer >80%, CB OPEN
 *
 * API Endpoint: GET /v1/kkt/buffer/status
 * Response: {buffer_percent, buffer_count, network_status, cb_state}
 */

import { Component, useState, onWillStart, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * Offline Indicator Component
 *
 * Displays real-time buffer status and network connectivity in POS UI.
 * Auto-refreshes every 30 seconds.
 */
export class OfflineIndicator extends Component {
    static template = "optics_pos_ru54fz.OfflineIndicator";

    setup() {
        this.rpc = useService("rpc");

        // State management
        this.state = useState({
            bufferPercent: 0,
            bufferCount: 0,
            networkStatus: 'unknown',  // 'online', 'offline', 'unknown'
            cbState: 'unknown',        // 'CLOSED', 'OPEN', 'HALF_OPEN', 'unknown'
            lastUpdate: null,
            error: null,
            loading: true,
        });

        // Polling interval (30 seconds)
        this.pollInterval = 30000;
        this.intervalId = null;

        // Initialize
        onWillStart(async () => {
            await this.fetchBufferStatus();
            this.startPolling();
        });

        // Cleanup on unmount
        onWillUnmount(() => {
            this.stopPolling();
        });
    }

    /**
     * Fetch buffer status from KKT adapter
     *
     * Calls: GET /v1/kkt/buffer/status
     * Returns: {buffer_percent, buffer_count, network_status, cb_state}
     */
    async fetchBufferStatus() {
        try {
            this.state.loading = true;
            this.state.error = null;

            // Call KKT adapter via Odoo controller
            const result = await this.rpc("/pos/kkt/buffer_status", {});

            // Update state
            this.state.bufferPercent = result.buffer_percent || 0;
            this.state.bufferCount = result.buffer_count || 0;
            this.state.networkStatus = result.network_status || 'unknown';
            this.state.cbState = result.cb_state || 'unknown';
            this.state.lastUpdate = new Date();
            this.state.loading = false;

        } catch (error) {
            console.error('Failed to fetch buffer status:', error);
            this.state.error = error.message || 'Connection error';
            this.state.loading = false;

            // Set fallback values on error
            this.state.networkStatus = 'offline';
            this.state.cbState = 'unknown';
        }
    }

    /**
     * Start polling every 30 seconds
     */
    startPolling() {
        if (this.intervalId) {
            return; // Already polling
        }

        this.intervalId = setInterval(() => {
            this.fetchBufferStatus();
        }, this.pollInterval);

        console.log(`[OfflineIndicator] Polling started (every ${this.pollInterval}ms)`);
    }

    /**
     * Stop polling
     */
    stopPolling() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
            console.log('[OfflineIndicator] Polling stopped');
        }
    }

    /**
     * Get status class for color coding
     *
     * Returns: 'status-green', 'status-yellow', 'status-red'
     */
    get statusClass() {
        const { networkStatus, bufferPercent, cbState } = this.state;

        // RED: Offline OR buffer >80% OR CB OPEN
        if (networkStatus === 'offline' || bufferPercent > 80 || cbState === 'OPEN') {
            return 'status-red';
        }

        // YELLOW: Buffer 50-80% OR CB HALF_OPEN
        if (bufferPercent >= 50 || cbState === 'HALF_OPEN') {
            return 'status-yellow';
        }

        // GREEN: Online, buffer <50%, CB CLOSED
        return 'status-green';
    }

    /**
     * Get status icon
     *
     * Returns: 'fa-check-circle', 'fa-exclamation-triangle', 'fa-times-circle'
     */
    get statusIcon() {
        const statusClass = this.statusClass;

        if (statusClass === 'status-green') {
            return 'fa-check-circle';
        } else if (statusClass === 'status-yellow') {
            return 'fa-exclamation-triangle';
        } else {
            return 'fa-times-circle';
        }
    }

    /**
     * Get status text
     *
     * Returns: 'Online', 'Warning', 'Offline'
     */
    get statusText() {
        const { networkStatus, bufferPercent, cbState } = this.state;

        if (networkStatus === 'offline') {
            return 'Offline';
        }

        if (bufferPercent > 80 || cbState === 'OPEN') {
            return 'Critical';
        }

        if (bufferPercent >= 50 || cbState === 'HALF_OPEN') {
            return 'Warning';
        }

        return 'Online';
    }

    /**
     * Get buffer status text
     *
     * Returns: '15 receipts (12%)'
     */
    get bufferStatusText() {
        const { bufferCount, bufferPercent } = this.state;
        return `${bufferCount} receipts (${Math.round(bufferPercent)}%)`;
    }

    /**
     * Get circuit breaker status text
     *
     * Returns: 'CB: CLOSED', 'CB: OPEN', 'CB: HALF_OPEN'
     */
    get cbStatusText() {
        const { cbState } = this.state;

        if (cbState === 'CLOSED') {
            return 'CB: CLOSED';
        } else if (cbState === 'OPEN') {
            return 'CB: OPEN';
        } else if (cbState === 'HALF_OPEN') {
            return 'CB: HALF_OPEN';
        } else {
            return 'CB: Unknown';
        }
    }

    /**
     * Get last update time
     *
     * Returns: '12:34:56'
     */
    get lastUpdateTime() {
        if (!this.state.lastUpdate) {
            return 'Never';
        }

        const date = this.state.lastUpdate;
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        const seconds = String(date.getSeconds()).padStart(2, '0');

        return `${hours}:${minutes}:${seconds}`;
    }

    /**
     * Manual refresh button handler
     */
    async onRefresh() {
        await this.fetchBufferStatus();
    }

    /**
     * Show detailed status modal
     */
    showDetails() {
        // TODO: Open modal with detailed buffer status, logs, and actions
        console.log('[OfflineIndicator] Show details (modal not implemented yet)');
    }
}

// Register component in POS registry
registry.category("pos_widgets").add("offline_indicator", {
    component: OfflineIndicator,
});

export default OfflineIndicator;
