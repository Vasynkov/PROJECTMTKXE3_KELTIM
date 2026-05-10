# TrigoQuest - Quizizz Edition (X-E3 Kelompok TIM)

Project edukasi matematika tentang Trigonometri (Kuadran & Sudut Istimewa) yang dirancang dengan antarmuka mirip Quizizz, lengkap dengan unsur anime dan fitur power-ups.

## Fitur Utama
- **UI Mirip Quizizz**: Tema ungu yang khas, kartu soal yang interaktif, dan animasi yang menarik.
- **Anime Theme**: Latar belakang pemandangan anime, maskot yang menemani permainan, dan feedback gif anime.
- **Power-Ups**: 
  - ⚡ **Double Points**: Mendapatkan skor 2x lipat.
  - ⚡ **Eraser**: Menghapus 2 pilihan jawaban salah.
  - ⚡ **Shield**: Melindungi streak saat jawaban salah.
- **Streak System**: Bonus poin untuk jawaban benar beruntun.
- **Leaderboard**: Pantau peringkatmu di antara pemain lain.
- **AI Summary**: Ringkasan materi instan untuk membantu belajar.

## Teknologi
- **Backend**: Flask (Python)
- **Database**: SQLite3
- **Frontend**: HTML5, CSS3 (Quicksand Font), JavaScript (Canvas Confetti)
- **Deployment**: Kompatibel dengan Vercel

## Cara Menjalankan Lokal
1. Install dependensi:
   ```bash
   pip install -r requirements.txt
   ```
2. Inisialisasi Database (jika belum ada):
   ```bash
   python database_setup.py
   ```
3. Jalankan aplikasi:
   ```bash
   python app.py
   ```
4. Akses di `http://127.0.0.1:5000`

## Deployment di Vercel
Aplikasi ini sudah dikonfigurasi untuk Vercel melalui `vercel.json`. Cukup hubungkan repository GitHub ke dashboard Vercel dan pilih framework Flask/Python.

---
**Developed with ❤️ by:**
- **Gilang Satria Pratama (cryesix_)** - Lead Programmer & Designer
- Dan seluruh anggota Kelompok Taman Ismail Marzuki (TIM) X-E3.
