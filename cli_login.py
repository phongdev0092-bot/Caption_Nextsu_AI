import sys
import core_login

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print("=" * 60)
    print("   FPT INSIDE AUTO LOGIN - CHẾ ĐỘ CHẠY TRỰC TIẾP")
    print("=" * 60)

    try:
        core_login.run_fpt_login(
            headless=False,
            keep_open=True,
            use_custom_profile=True
        )
        print("\n[OK] Đã hoàn thành quá trình đăng nhập.")
    except Exception as e:
        print(f"\n[LỖI] Đăng nhập thất bại: {e}")

if __name__ == "__main__":
    main()
