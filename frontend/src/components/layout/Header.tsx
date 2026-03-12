import Link from 'next/link';

export function Header() {
  return (
    <header className="bg-white shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <Link href="/" className="text-xl font-bold text-gray-900">
            Badgers MVP
          </Link>
          <nav className="flex gap-6">
            <Link
              href="/projects"
              className="text-gray-600 hover:text-gray-900"
            >
              Projects
            </Link>
          </nav>
        </div>
      </div>
    </header>
  );
}
