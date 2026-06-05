from __future__ import annotations

import shlex
from dataclasses import dataclass

from cafe_order_kiosk.models import OrderStatus, OPTION_PRICES
from cafe_order_kiosk.kiosk_store import KioskStore
from cafe_order_kiosk.utils import format_money


@dataclass
class CLIState:
    current_order_id: int | None = None


def run_cli() -> int:
    store = KioskStore.with_default_menu()
    state = CLIState()

    print("카페 주문 키오스크")
    print("명령어 목록은 '도움말'을 입력하세요. 가격은 원 단위 정수입니다.")

    while True:
        try:
            raw = input("kiosk> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not raw:
            continue

        tokens = shlex.split(raw)
        command, args = tokens[0], tokens[1:]

        if command in {"종료", "끝", "quit", "exit"}:
            break
        elif command in {"도움말", "help"}:
            print_help()
        elif command in {"메뉴", "menu"}:
            handle_menu(store)
        elif command in {"주문", "order"}:
            handle_order(store, state, args)
        elif command in {"주문목록", "orders"}:
            handle_orders(store, args)
        elif command in {"결제", "pay"}:
            handle_pay(store, state, args)
        elif command in {"통계", "stats"}:
            handle_stats(store)
        else:
            print("알 수 없는 명령입니다. '도움말'을 입력하세요.")
    print("종료합니다.")
    return 0


def print_help() -> None:
    print("명령어:")
    print("\t메뉴")
    print("\t주문 생성 [메모]")
    print("\t주문 선택 <주문_id>")
    print("\t주문 추가 <메뉴_id> <수량> [옵션]")
    print("\t주문 삭제 <라인번호>")
    print("\t주문 조회")
    print("\t주문 취소")
    print("\t주문목록 목록 [진행중|결제완료|취소]")
    print("\t결제 <방법> [금액]")
    print("\t통계")
    print("\t도움말")
    print("\t종료")


def handle_menu(store: KioskStore) -> None:
    print("메뉴 목록:")
    print("  * 세트 자동 할인: 음료(coffee, tea, juice) 1개 + 디저트/베이커리(bakery, dessert) 1개 동시 주문 시 세트당 500원 자동 할인!")

    items = store.list_menu()
    beverages: dict[str, list[MenuItem]] = {}
    desserts: dict[str, list[MenuItem]] = {}
    others: dict[str, list[MenuItem]] = {}

    for item in items:
        cat = item.category or "기타"
        if cat in {"coffee", "tea", "juice"}:
            beverages.setdefault(cat, []).append(item)
        elif cat in {"bakery", "dessert"}:
            desserts.setdefault(cat, []).append(item)
        else:
            others.setdefault(cat, []).append(item)

    if beverages:
        print("\n  [ 음료 (세트할인 대상) ]")
        for cat_name in ["coffee", "tea", "juice"]:
            if cat_name in beverages:
                print(f"    * {cat_name.upper()}")
                for item in beverages[cat_name]:
                    desc = f" - {item.description}" if item.description else ""
                    print(f"\t{item.id}. {item.name} - {format_money(item.price)}원{desc}")

    if desserts:
        print("\n  [ 디저트/베이커리 (세트할인 대상) ]")
        for cat_name in ["bakery", "dessert"]:
            if cat_name in desserts:
                print(f"    * {cat_name.upper()}")
                for item in desserts[cat_name]:
                    desc = f" - {item.description}" if item.description else ""
                    print(f"\t{item.id}. {item.name} - {format_money(item.price)}원{desc}")

    if others:
        print("\n  [ 기타 ]")
        for cat_name, item_list in others.items():
            print(f"    * {cat_name.upper()}")
            for item in item_list:
                desc = f" - {item.description}" if item.description else ""
                print(f"\t{item.id}. {item.name} - {format_money(item.price)}원{desc}")

    print("\n  추가 가능한 옵션:")
    for opt, price in OPTION_PRICES.items():
        print(f"    - {opt}: +{format_money(price)}원")


def handle_order(store: KioskStore, state: CLIState, args: list[str]) -> None:
    if not args:
        print("주문 명령어: 생성, 선택, 추가, 삭제, 조회, 취소")
        return

    action, tail = args[0], args[1:]

    if action in {"생성", "new"}:
        note = " ".join(tail).strip() if tail else None
        order = store.create_order(note=note)
        state.current_order_id = order.id
        print(f"주문 #{order.id}가 생성되었습니다.")
    elif action in {"선택", "select"}:
        order_id = parse_int_arg(tail, "order_id")
        if order_id is None:
            return
        order = store.get_order(order_id)
        if order is None:
            print("주문을 찾을 수 없습니다.")
            return
        state.current_order_id = order.id
        print(f"주문 #{order.id}를 선택했습니다.")
    elif action in {"추가", "add"}:
        if state.current_order_id is None:
            print("선택된 주문이 없습니다. 먼저 '주문 생성'을 사용하세요.")
            return
        if len(tail) < 2:
            print("사용법: 주문 추가 <메뉴_id> <수량> [옵션]")
            return
        menu_id = parse_int_arg(tail[:1], "menu_id")
        quantity = parse_int_arg(tail[1:2], "qty")
        if menu_id is None or quantity is None:
            return

        options_text = " ".join(tail[2:]).strip()
        options = (
            [option.strip() for option in options_text.split(",") if option.strip()]
            if options_text
            else []
        )
        try:
            store.add_item(state.current_order_id, menu_id, quantity, options)
        except ValueError as exc:
            print(str(exc))
            return
        print("항목이 추가되었습니다.")
    elif action in {"삭제", "remove"}:
        if state.current_order_id is None:
            print("선택된 주문이 없습니다. 먼저 '주문 생성'을 사용하세요.")
            return
        line_index = parse_int_arg(tail, "line_index")
        if line_index is None:
            return
        try:
            store.remove_item(state.current_order_id, line_index)
        except ValueError as exc:
            print(str(exc))
            return
        print("항목이 삭제되었습니다.")
    elif action in {"조회", "show"}:
        if state.current_order_id is None:
            print("선택된 주문이 없습니다. 먼저 '주문 생성'을 사용하세요.")
            return
        order = store.get_order(state.current_order_id)
        if order is None:
            print("주문을 찾을 수 없습니다.")
            return
        print_order(order)
    elif action in {"취소", "cancel"}:
        if state.current_order_id is None:
            print("선택된 주문이 없습니다. 먼저 '주문 생성'을 사용하세요.")
            return
        try:
            order = store.cancel_order(state.current_order_id)
        except ValueError as exc:
            print(str(exc))
            return
        print(f"주문 #{order.id}가 취소되었습니다.")
    else:
        print("알 수 없는 주문 명령어입니다.")


def handle_orders(store: KioskStore, args: list[str]) -> None:
    if not args or args[0] not in {"list", "목록"}:
        print("사용법: 주문목록 목록 [진행중|결제완료|취소]")
        return

    status = None
    if len(args) > 1:
        status = parse_status(args[1])
        if status is None:
            return

    orders = store.list_orders(status)
    if not orders:
        print("주문이 없습니다.")
        return

    for order in orders:
        print(
            f"  #{order.id} {format_status(order.status)} - {format_money(order.total)}"
        )


def handle_pay(store: KioskStore, state: CLIState, args: list[str]) -> None:
    if state.current_order_id is None:
        print("선택된 주문이 없습니다. 먼저 '주문 생성'을 사용하세요.")
        return
    if not args:
        print("사용법: 결제 <방법> [금액]")
        return

    method = args[0]
    amount = None
    if len(args) > 1:
        amount = parse_int_arg(args[1:2], "amount")
        if amount is None:
            return

    order = store.get_order(state.current_order_id)
    if order is None:
        print("주문을 찾을 수 없습니다.")
        return
    if amount is None:
        amount = order.total

    try:
        store.pay_order(order.id, method, amount)
    except ValueError as exc:
        print(str(exc))
        return

    print(f"주문 #{order.id} 결제 완료 ({method}).")


def print_order(order) -> None:
    print(f"주문 #{order.id} ({format_status(order.status)})")
    if order.note:
        print(f"메모: {order.note}")
    if not order.items:
        print("  (비어 있음)")
        return

    for idx, item in enumerate(order.items, start=1):
        options_detail = []
        for opt in item.options:
            surch = OPTION_PRICES.get(opt.strip(), 0)
            if surch > 0:
                options_detail.append(f"{opt}(+{format_money(surch)})")
            else:
                options_detail.append(opt)
        options = f" [{', '.join(options_detail)}]" if item.options else ""
        print(
            f"  {idx}. {item.name}{options} x{item.quantity}"
            f" - {format_money(item.line_total)}"
        )
    if order.discount > 0:
        print(f"  할인 (세트 할인): -{format_money(order.discount)}")
    print(f"합계: {format_money(order.total)}")


def parse_int_arg(args: list[str], name: str) -> int | None:
    if not args:
        print(f"필수 값이 없습니다: {name}")
        return None
    try:
        return int(args[0])
    except ValueError:
        print(f"잘못된 값: {name}")
        return None


def parse_status(raw: str) -> OrderStatus | None:
    normalized = raw.lower()
    status_map = {
        "open": OrderStatus.OPEN,
        "paid": OrderStatus.PAID,
        "canceled": OrderStatus.CANCELED,
        "진행중": OrderStatus.OPEN,
        "결제완료": OrderStatus.PAID,
        "취소": OrderStatus.CANCELED,
    }
    status = status_map.get(normalized)
    if status is None:
        print("잘못된 상태입니다. 진행중, 결제완료, 취소 중에서 선택하세요.")
    return status

def format_status(status: OrderStatus) -> str:
    status_map = {
        OrderStatus.OPEN: "진행중",
        OrderStatus.PAID: "결제완료",
        OrderStatus.CANCELED: "취소",
    }
    return status_map.get(status, status.value)


def handle_stats(store: KioskStore) -> None:
    stats = store.get_sales_analytics()

    print("========================================")
    print("            매출 통계 리포트            ")
    print("========================================")

    print("[ 오늘 매출 현황 ]")
    print(f"  - 총 결제 주문 건수: {stats.today_paid_orders_count} 건")
    print(f"  - 오늘 하루 매출액  : {format_money(stats.today_sales_amount)} 원")

    print("\n[ 결제 수단별 건수 (누적) ]")
    if not stats.payment_methods:
        print("  - 내역 없음")
    else:
        for method, count in stats.payment_methods.items():
            print(f"  - {method}: {count} 건")

    print("\n[ 가장 많이 팔린 메뉴 Top 3 (누적) ]")
    if not stats.top_menu_items:
        print("  - 내역 없음")
    else:
        for idx, (name, qty) in enumerate(stats.top_menu_items, start=1):
            print(f"  {idx}. {name} ({qty} 개)")

    print("\n[ 피크 시간대 분석 (누적) ]")
    if not stats.peak_hours:
        print("  - 내역 없음")
    else:
        top_hour, top_count = stats.peak_hours[0]
        print(f"  - 가장 주문이 많았던 시간: {top_hour:02d}시 ({top_count} 건)")
        distribution = ", ".join(f"{h:02d}시({c}건)" for h, c in sorted(stats.peak_hours))
        print(f"  - 시간대별 분포: {distribution}")

    print("========================================")

