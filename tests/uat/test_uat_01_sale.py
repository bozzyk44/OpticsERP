"""
UAT-01: Sale with Prescription (End-to-End Test)

Author: AI Agent
Created: 2025-11-29
Task: OPTERP-50 (Create UAT-01 Sale Test)

Test Scenario:
Customer purchases eyeglasses with custom prescription:
1. Create customer in Odoo
2. Create prescription in Odoo
3. Create sale order (frame + lenses + prescription)
4. Process payment in POS
5. Print fiscal receipt via KKT adapter
6. Verify receipt in buffer
7. Wait for OFD sync
8. Verify receipt synced

Business Flow:
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Odoo POS  │────>│ KKT Adapter │────>│   Buffer    │────>│     OFD     │
│             │     │  (Print)    │     │  (Pending)  │     │  (Synced)   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘

Acceptance Criteria:
- ✅ Sale order created with prescription
- ✅ Receipt printed via KKT
- ✅ Receipt stored in buffer
- ✅ Receipt synced to OFD within 60s
- ✅ End-to-end flow works without errors

Reference: CLAUDE.md §8 (UAT Testing)
"""

import pytest
import time
import requests
from typing import Dict, Any


# ====================
# UAT-01: Sale with Prescription
# ====================

class TestUAT01Sale:
    """
    UAT-01: Sale with Prescription

    End-to-end test for eyeglasses sale with custom prescription.
    """

    @pytest.mark.uat
    @pytest.mark.skip(reason="Requires Odoo to be running")
    def test_uat_01_sale_with_prescription_full_flow(
        self,
        odoo_env,
        sample_customer,
        sample_prescription,
        sample_lens,
        sample_frame,
        kkt_adapter_health,
        clean_buffer,
    ):
        """
        UAT-01: Sale with Prescription (Full End-to-End Flow)

        Scenario:
        1. Create customer
        2. Create prescription
        3. Create sale order (frame + lenses)
        4. Create POS order
        5. Process payment
        6. Print fiscal receipt
        7. Verify buffer
        8. Verify OFD sync

        This test requires:
        - Odoo running on localhost:8069
        - KKT adapter running on localhost:8000
        - Mock OFD server running on localhost:9000 (or real OFD)
        """
        # Step 1: Create customer
        customer = odoo_env['res.partner'].create({
            'name': sample_customer['name'],
            'phone': sample_customer['phone'],
            'email': sample_customer['email'],
            'street': sample_customer['street'],
            'city': sample_customer['city'],
            'zip': sample_customer['zip'],
        })

        assert customer.id, "Customer creation failed"
        print(f"✅ Customer created: {customer.name} (ID: {customer.id})")

        # Step 2: Create prescription
        prescription = odoo_env['optics.prescription'].create({
            'partner_id': customer.id,
            'right_sph': sample_prescription['right_eye']['sph'],
            'right_cyl': sample_prescription['right_eye']['cyl'],
            'right_axis': sample_prescription['right_eye']['axis'],
            'right_add': sample_prescription['right_eye']['add'],
            'left_sph': sample_prescription['left_eye']['sph'],
            'left_cyl': sample_prescription['left_eye']['cyl'],
            'left_axis': sample_prescription['left_eye']['axis'],
            'left_add': sample_prescription['left_eye']['add'],
            'pd': sample_prescription['pd'],
            'notes': sample_prescription['notes'],
        })

        assert prescription.id, "Prescription creation failed"
        print(f"✅ Prescription created (ID: {prescription.id})")

        # Step 3: Create sale order
        sale_order = odoo_env['sale.order'].create({
            'partner_id': customer.id,
            'prescription_id': prescription.id,
        })

        # Add frame product
        frame_product = odoo_env['product.product'].search([
            ('name', 'ilike', 'frame')
        ], limit=1)

        if not frame_product:
            # Create frame product if not exists
            frame_product = odoo_env['product.product'].create({
                'name': f"{sample_frame['brand']} {sample_frame['model']}",
                'list_price': sample_frame['price'],
                'type': 'product',
            })

        odoo_env['sale.order.line'].create({
            'order_id': sale_order.id,
            'product_id': frame_product.id,
            'product_uom_qty': 1,
            'price_unit': sample_frame['price'],
        })

        # Add lens product
        lens_product = odoo_env['product.product'].search([
            ('name', 'ilike', 'lens')
        ], limit=1)

        if not lens_product:
            # Create lens product if not exists
            lens_product = odoo_env['product.product'].create({
                'name': f"Lens {sample_lens['lens_type']} {sample_lens['index']}",
                'list_price': sample_lens['price'],
                'type': 'product',
            })

        odoo_env['sale.order.line'].create({
            'order_id': sale_order.id,
            'product_id': lens_product.id,
            'product_uom_qty': 2,  # 2 lenses
            'price_unit': sample_lens['price'],
        })

        # Confirm sale order
        sale_order.action_confirm()

        assert sale_order.state == 'sale', "Sale order confirmation failed"
        print(f"✅ Sale order created and confirmed (ID: {sale_order.id}, Total: {sale_order.amount_total})")

        # Step 4: Create POS order
        pos_config = odoo_env['pos.config'].search([], limit=1)
        if not pos_config:
            pytest.skip("No POS config found - create one in Odoo first")

        pos_session = odoo_env['pos.session'].search([
            ('config_id', '=', pos_config.id),
            ('state', '=', 'opened')
        ], limit=1)

        if not pos_session:
            # Open new POS session
            pos_session = odoo_env['pos.session'].create({
                'config_id': pos_config.id,
            })
            pos_session.action_pos_session_open()

        # Create POS order
        pos_order = odoo_env['pos.order'].create({
            'session_id': pos_session.id,
            'partner_id': customer.id,
            'prescription_id': prescription.id,
            'lines': [(0, 0, {
                'product_id': frame_product.id,
                'qty': 1,
                'price_unit': sample_frame['price'],
            }), (0, 0, {
                'product_id': lens_product.id,
                'qty': 2,
                'price_unit': sample_lens['price'],
            })],
        })

        assert pos_order.id, "POS order creation failed"
        print(f"✅ POS order created (ID: {pos_order.id})")

        # Step 5: Process payment
        payment = odoo_env['pos.payment'].create({
            'pos_order_id': pos_order.id,
            'amount': pos_order.amount_total,
            'payment_method_id': odoo_env['pos.payment.method'].search([], limit=1).id,
        })

        pos_order.action_pos_order_paid()

        assert pos_order.state == 'paid', "Payment processing failed"
        print(f"✅ Payment processed (Amount: {pos_order.amount_total})")

        # Step 6: Print fiscal receipt via KKT adapter
        kkt_adapter_url = kkt_adapter_health

        receipt_data = {
            "pos_id": pos_config.name,
            "order_id": pos_order.name,
            "type": "sale",
            "items": [
                {
                    "name": frame_product.name,
                    "price": sample_frame['price'],
                    "quantity": 1,
                    "total": sample_frame['price'],
                    "vat_rate": 20,
                },
                {
                    "name": lens_product.name,
                    "price": sample_lens['price'],
                    "quantity": 2,
                    "total": sample_lens['price'] * 2,
                    "vat_rate": 20,
                }
            ],
            "payments": [
                {
                    "type": "cash",
                    "amount": pos_order.amount_total,
                }
            ],
            "total": pos_order.amount_total,
            "customer": {
                "name": customer.name,
                "phone": customer.phone,
                "email": customer.email,
            },
        }

        response = requests.post(
            f"{kkt_adapter_url}/v1/kkt/receipt",
            json=receipt_data,
            headers={"Idempotency-Key": f"uat01-{pos_order.id}"},
            timeout=10,
        )

        assert response.status_code == 200, f"Receipt print failed: {response.text}"

        fiscal_doc_id = response.json().get('fiscal_doc_id')
        assert fiscal_doc_id, "Fiscal document ID not returned"

        print(f"✅ Receipt printed (Fiscal Doc ID: {fiscal_doc_id})")

        # Step 7: Verify receipt in buffer
        buffer_response = requests.get(
            f"{kkt_adapter_url}/v1/kkt/buffer/status",
            timeout=5,
        )

        assert buffer_response.status_code == 200, "Buffer status check failed"

        buffer_data = buffer_response.json()
        assert buffer_data['buffer_count'] > 0, "Receipt not found in buffer"

        print(f"✅ Receipt in buffer (Count: {buffer_data['buffer_count']}, Status: {buffer_data.get('network_status')})")

        # Step 8: Wait for OFD sync (max 60 seconds)
        print("⏳ Waiting for OFD sync...")

        sync_timeout = 60
        start_time = time.time()
        synced = False

        while time.time() - start_time < sync_timeout:
            # Check buffer status
            buffer_response = requests.get(
                f"{kkt_adapter_url}/v1/kkt/buffer/status",
                timeout=5,
            )

            if buffer_response.status_code == 200:
                buffer_data = buffer_response.json()

                # If buffer empty or count decreased, assume synced
                if buffer_data['buffer_count'] == 0:
                    synced = True
                    break

            time.sleep(2)  # Poll every 2 seconds

        assert synced, f"Receipt not synced within {sync_timeout}s"

        print(f"✅ Receipt synced to OFD (Duration: {time.time() - start_time:.2f}s)")

        # Final verification
        print("\n=== UAT-01 PASSED ===")
        print(f"Customer: {customer.name}")
        print(f"Prescription: {prescription.id}")
        print(f"Sale Order: {sale_order.name} ({sale_order.amount_total} RUB)")
        print(f"POS Order: {pos_order.name}")
        print(f"Fiscal Doc: {fiscal_doc_id}")
        print(f"Status: ✅ SYNCED")


    @pytest.mark.uat
    @pytest.mark.smoke
    def test_uat_01_sale_smoke_test_kkt_only(
        self,
        kkt_adapter_health,
        clean_buffer,
    ):
        """
        UAT-01: Smoke Test (KKT Adapter Only)

        Simplified version of UAT-01 that tests only KKT adapter
        without requiring Odoo.

        This test verifies:
        - KKT adapter receives receipt
        - Receipt stored in buffer
        - Receipt can be retrieved

        Use this for quick smoke testing of KKT adapter functionality.
        """
        kkt_adapter_url = kkt_adapter_health

        # Create minimal receipt data
        receipt_data = {
            "pos_id": "POS-UAT-01",
            "order_id": "UAT01-SMOKE",
            "type": "sale",
            "items": [
                {
                    "name": "Frame (Smoke Test)",
                    "price": 3000.00,
                    "quantity": 1,
                    "total": 3000.00,
                    "vat_rate": 20,
                },
                {
                    "name": "Lenses (Smoke Test)",
                    "price": 5000.00,
                    "quantity": 2,
                    "total": 10000.00,
                    "vat_rate": 20,
                }
            ],
            "payments": [
                {
                    "type": "cash",
                    "amount": 13000.00,
                }
            ],
            "total": 13000.00,
        }

        # Step 1: Print receipt
        response = requests.post(
            f"{kkt_adapter_url}/v1/kkt/receipt",
            json=receipt_data,
            headers={"Idempotency-Key": f"uat01-smoke-{int(time.time())}"},
            timeout=10,
        )

        assert response.status_code == 200, f"Receipt print failed: {response.text}"

        fiscal_doc_id = response.json().get('fiscal_doc_id')
        assert fiscal_doc_id, "Fiscal document ID not returned"

        print(f"✅ Receipt printed (Fiscal Doc ID: {fiscal_doc_id})")

        # Step 2: Verify receipt in buffer
        buffer_response = requests.get(
            f"{kkt_adapter_url}/v1/kkt/buffer/status",
            timeout=5,
        )

        assert buffer_response.status_code == 200, "Buffer status check failed"

        buffer_data = buffer_response.json()
        assert buffer_data['buffer_count'] > 0, "Receipt not found in buffer"

        print(f"✅ Receipt in buffer (Count: {buffer_data['buffer_count']})")

        # Step 3: Success
        print("\n=== UAT-01 SMOKE TEST PASSED ===")
        print(f"Fiscal Doc: {fiscal_doc_id}")
        print(f"Buffer Count: {buffer_data['buffer_count']}")
        print(f"Status: ✅ BUFFERED")


# ====================
# Summary
# ====================
"""
Test Summary:

UAT-01: Sale with Prescription
- test_uat_01_sale_with_prescription_full_flow() - Full end-to-end test (requires Odoo)
- test_uat_01_sale_smoke_test_kkt_only() - Smoke test (KKT adapter only)

Run Tests:
# Full UAT-01 (requires Odoo)
pytest tests/uat/test_uat_01_sale.py::TestUAT01Sale::test_uat_01_sale_with_prescription_full_flow -v

# Smoke test only (no Odoo required)
pytest tests/uat/test_uat_01_sale.py::TestUAT01Sale::test_uat_01_sale_smoke_test_kkt_only -v

# All UAT tests
pytest tests/uat/test_uat_01_sale.py -v

# All UAT tests with marker
pytest -m uat tests/uat/ -v

# Smoke tests only
pytest -m smoke tests/uat/ -v
"""
