# Tài liệu Finvista

Mục lục tài liệu trong thư mục `docs/` — tên file theo thứ tự đọc, dùng **kebab-case** (chữ thường, nối bằng dấu gạch ngang).

## Tài liệu chính

| File | Nội dung |
|------|----------|
| [01-saas-architecture-blueprint.md](./01-saas-architecture-blueprint.md) | Kiến trúc SaaS web/mobile & kế hoạch triển khai |
| [02-unified-integration-plan.md](./02-unified-integration-plan.md) | Kế hoạch hợp nhất CW + Financial Distress |
| [03-financial-distress-roadmap.md](./03-financial-distress-roadmap.md) | Roadmap hệ thống dự báo kiệt quệ tài chính |
| [04-chuong-5-phan-tich-tai-chinh.md](./04-chuong-5-phan-tich-tai-chinh.md) | Chương 5: CAPEX, OPEX, doanh thu |
| [05-bao-cao-nhom-extracted.md](./05-bao-cao-nhom-extracted.md) | Nội dung trích xuất từ báo cáo PDF |
| [finvista-nhom-1-bao-cao.pdf](./finvista-nhom-1-bao-cao.pdf) | Báo cáo nhóm gốc (PDF) |

## Hình ảnh slide (`img/`)

12 slide từ báo cáo, đặt tên theo thứ tự: `slide-01.png` … `slide-12.png`.

## Công cụ liên quan

- Trích xuất PDF: `python tools/read_pdf.py` (đọc `docs/finvista-nhom-1-bao-cao.pdf`)
- Xem metadata ảnh: `python tools/inspect_images.py` (chạy trong `docs/img`)
