import pytest

from cafe_order_kiosk.kiosk_store import KioskStore
from cafe_order_kiosk.models import OrderStatus


def test_create_order_and_add_items_total() -> None:
    store = KioskStore.with_default_menu()
    order = store.create_order(note="hot")

    store.add_item(order.id, menu_item_id=1, quantity=2, options=["ice"])
    store.add_item(order.id, menu_item_id=2, quantity=1)

    order = store.get_order(order.id)
    assert order is not None
    assert order.total == 3500 * 2 + 4000
    assert order.status is OrderStatus.OPEN


def test_remove_item_updates_total() -> None:
    store = KioskStore.with_default_menu()
    order = store.create_order()

    store.add_item(order.id, menu_item_id=1, quantity=1)
    store.add_item(order.id, menu_item_id=2, quantity=1)
    store.remove_item(order.id, line_index=1)

    order = store.get_order(order.id)
    assert order is not None
    assert order.total == 4000


def test_pay_order_success() -> None:
    store = KioskStore.with_default_menu()
    order = store.create_order()

    store.add_item(order.id, menu_item_id=1, quantity=1)
    store.pay_order(order.id, method="card", amount=3500)

    order = store.get_order(order.id)
    assert order is not None
    assert order.status is OrderStatus.PAID
    assert order.payment is not None
    assert order.payment.method == "card"


def test_pay_order_amount_mismatch() -> None:
    store = KioskStore.with_default_menu()
    order = store.create_order()

    store.add_item(order.id, menu_item_id=1, quantity=1)

    with pytest.raises(ValueError, match="Payment amount does not match total"):
        store.pay_order(order.id, method="card", amount=1000)


def test_cancel_paid_order_is_error() -> None:
    store = KioskStore.with_default_menu()
    order = store.create_order()

    store.add_item(order.id, menu_item_id=1, quantity=1)
    store.pay_order(order.id, method="card", amount=3500)

    with pytest.raises(ValueError, match="Paid order cannot be canceled"):
        store.cancel_order(order.id)


def test_order_item_option_surcharges() -> None:
    store = KioskStore.with_default_menu()
    order = store.create_order()

    # Menu 1 is Americano (3500)
    # Adding 1 Americano with "샷추가" (+500) and "사이즈업" (+1000)
    # Total should be (3500 + 500 + 1000) * 1 = 5000
    store.add_item(order.id, menu_item_id=1, quantity=1, options=["샷추가", "사이즈업"])

    # Adding 2 Lattes (4000) with "디카페인" (+300) and a free option "ice" (+0)
    # Total should be (4000 + 300) * 2 = 8600
    store.add_item(order.id, menu_item_id=2, quantity=2, options=["디카페인", "ice"])

    order = store.get_order(order.id)
    assert order is not None
    assert order.items[0].surcharge == 1500
    assert order.items[0].line_total == 5000
    assert order.items[1].surcharge == 300
    assert order.items[1].line_total == 8600
    assert order.total == 5000 + 8600


def test_set_menu_discount_single() -> None:
    store = KioskStore.with_default_menu()
    order = store.create_order()

    # 1 Americano (3500) + 1 Butter Croissant (3500)
    store.add_item(order.id, menu_item_id=1, quantity=1)
    store.add_item(order.id, menu_item_id=8, quantity=1)

    order = store.get_order(order.id)
    assert order is not None
    assert order.discount == 500
    assert order.total == (3500 + 3500) - 500


def test_set_menu_discount_multiple() -> None:
    store = KioskStore.with_default_menu()
    order = store.create_order()

    # 2 Americano (3500 * 2 = 7000)
    store.add_item(order.id, menu_item_id=1, quantity=2)
    # 1 Butter Croissant (3500)
    store.add_item(order.id, menu_item_id=8, quantity=1)
    # 1 Cheesecake (5200)
    store.add_item(order.id, menu_item_id=10, quantity=1)

    order = store.get_order(order.id)
    assert order is not None
    # 2 beverages, 2 bakery/dessert -> 2 sets
    assert order.discount == 1000
    assert order.total == (7000 + 3500 + 5200) - 1000


def test_set_menu_discount_none() -> None:
    store = KioskStore.with_default_menu()
    order = store.create_order()

    # 2 Lattes (4000 * 2 = 8000)
    store.add_item(order.id, menu_item_id=2, quantity=2)

    order = store.get_order(order.id)
    assert order is not None
    assert order.discount == 0
    assert order.total == 8000


def test_print_order_discount(capsys: pytest.CaptureFixture[str]) -> None:
    from cafe_order_kiosk.cli import print_order
    store = KioskStore.with_default_menu()
    order = store.create_order()
    store.add_item(order.id, menu_item_id=1, quantity=1)
    store.add_item(order.id, menu_item_id=8, quantity=1)

    order = store.get_order(order.id)
    assert order is not None
    print_order(order)

    captured = capsys.readouterr()
    assert "할인 (세트 할인): -500" in captured.out
    assert "합계: 6,500" in captured.out


def test_handle_menu_set_tags(capsys: pytest.CaptureFixture[str]) -> None:
    from cafe_order_kiosk.cli import handle_menu
    store = KioskStore.with_default_menu()
    handle_menu(store)

    captured = capsys.readouterr()
    assert "세트 자동 할인" in captured.out
    assert "[ 음료 (세트할인 대상) ]" in captured.out
    assert "[ 디저트/베이커리 (세트할인 대상) ]" in captured.out




