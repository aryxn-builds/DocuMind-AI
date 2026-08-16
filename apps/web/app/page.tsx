import Link from 'next/link'
import { FileText, Search, Shield, Zap, CheckCircle2, MessageSquare, Database, ArrowRight } from 'lucide-react'

export default function HomePage() {
  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-50 font-sans selection:bg-zinc-200 dark:selection:bg-zinc-800">
      {/* Navbar */}
      <header className="sticky top-0 z-50 w-full border-b border-zinc-200 dark:border-zinc-800/50 bg-white/80 dark:bg-zinc-950/80 backdrop-blur-md">
        <div className="container mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-zinc-900 dark:bg-zinc-100 text-zinc-50 dark:text-zinc-900 rounded-md flex items-center justify-center font-bold text-xl leading-none">
              D
            </div>
            <span className="font-semibold text-lg tracking-tight">DocuMind AI</span>
          </div>
          <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-zinc-600 dark:text-zinc-400">
            <a href="#features" className="hover:text-zinc-900 dark:hover:text-zinc-100 transition-colors">Features</a>
            <a href="#how-it-works" className="hover:text-zinc-900 dark:hover:text-zinc-100 transition-colors">How it Works</a>
          </nav>
          <div className="flex items-center gap-4">
            <Link 
              href="/login" 
              className="hidden sm:block text-sm font-medium text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100 transition-colors"
            >
              Sign In
            </Link>
            <Link 
              href="/signup" 
              className="bg-zinc-900 text-zinc-50 hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200 px-4 py-2 rounded-full text-sm font-medium transition-colors"
            >
              Get Started
            </Link>
          </div>
        </div>
      </header>

      <main>
        {/* Hero Section */}
        <section className="relative pt-24 pb-32 overflow-hidden">
          <div className="container mx-auto px-6 flex flex-col items-center text-center">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-xs font-medium text-zinc-600 dark:text-zinc-400 mb-8">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-zinc-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-zinc-500"></span>
              </span>
              v0.1.0 is now live
            </div>
            
            <h1 className="text-5xl md:text-7xl font-bold tracking-tighter mb-6 max-w-4xl leading-[1.1]">
              Chat with your documents using <span className="text-transparent bg-clip-text bg-gradient-to-r from-zinc-500 to-zinc-900 dark:from-zinc-400 dark:to-zinc-100">AI.</span>
            </h1>
            
            <p className="text-lg md:text-xl text-zinc-600 dark:text-zinc-400 mb-10 max-w-2xl leading-relaxed">
              Upload PDFs and other supported documents, let DocuMind understand them, and ask grounded questions with citations. No more skimming through endless pages.
            </p>
            
            <div className="flex flex-col sm:flex-row items-center gap-4 w-full sm:w-auto">
              <Link 
                href="/signup" 
                className="w-full sm:w-auto bg-zinc-900 text-zinc-50 hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200 px-8 py-3.5 rounded-full text-base font-medium transition-colors flex items-center justify-center gap-2"
              >
                Get Started <ArrowRight className="w-4 h-4" />
              </Link>
              <Link 
                href="/login" 
                className="w-full sm:w-auto bg-white text-zinc-900 border border-zinc-200 hover:bg-zinc-50 dark:bg-zinc-950 dark:text-zinc-100 dark:border-zinc-800 dark:hover:bg-zinc-900 px-8 py-3.5 rounded-full text-base font-medium transition-colors flex items-center justify-center"
              >
                Sign In
              </Link>
            </div>
          </div>
        </section>

        {/* Product Preview Section */}
        <section className="container mx-auto px-6 mb-32">
          <div className="relative mx-auto max-w-5xl rounded-xl sm:rounded-2xl border border-zinc-200/50 dark:border-zinc-800/50 bg-white/50 dark:bg-zinc-900/50 p-2 sm:p-4 backdrop-blur-sm shadow-2xl shadow-zinc-200/20 dark:shadow-black/40 overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-tr from-transparent via-zinc-100/50 to-transparent dark:via-zinc-800/20 pointer-events-none" />
            <div className="rounded-lg sm:rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 overflow-hidden flex flex-col md:flex-row shadow-sm relative z-10 h-[400px] md:h-[500px]">
              {/* Mock Sidebar / Doc Info */}
              <div className="hidden md:flex flex-col w-64 border-r border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/30 p-4">
                <div className="flex items-center gap-2 mb-6">
                  <div className="w-8 h-8 rounded bg-zinc-200 dark:bg-zinc-800 flex items-center justify-center">
                    <FileText className="w-4 h-4 text-zinc-500" />
                  </div>
                  <div>
                    <div className="text-sm font-medium leading-none">Q3_Report.pdf</div>
                    <div className="text-xs text-zinc-500 mt-1">Ready</div>
                  </div>
                </div>
                <div className="space-y-3">
                  <div className="h-2 bg-zinc-200 dark:bg-zinc-800 rounded w-full"></div>
                  <div className="h-2 bg-zinc-200 dark:bg-zinc-800 rounded w-4/5"></div>
                  <div className="h-2 bg-zinc-200 dark:bg-zinc-800 rounded w-5/6"></div>
                </div>
              </div>
              
              {/* Mock Chat Panel */}
              <div className="flex-1 flex flex-col">
                <div className="border-b border-zinc-200 dark:border-zinc-800 p-4">
                  <h3 className="font-medium text-sm">AI Assistant</h3>
                </div>
                <div className="flex-1 p-4 space-y-4 overflow-hidden relative">
                  <div className="flex justify-end">
                    <div className="bg-zinc-900 text-zinc-50 dark:bg-zinc-100 dark:text-zinc-900 px-4 py-2.5 rounded-2xl rounded-tr-sm text-sm max-w-[85%]">
                      What were the key takeaways from Q3?
                    </div>
                  </div>
                  <div className="flex justify-start">
                    <div className="bg-zinc-100 text-zinc-900 dark:bg-zinc-900 dark:text-zinc-100 border border-zinc-200 dark:border-zinc-800 px-4 py-3 rounded-2xl rounded-tl-sm text-sm max-w-[85%]">
                      <p className="mb-2">Based on the document, the key takeaways from Q3 are:</p>
                      <ul className="list-disc pl-4 space-y-1 mb-3 text-zinc-700 dark:text-zinc-300">
                        <li>Revenue increased by 15% year-over-year.</li>
                        <li>Customer retention improved to 92%.</li>
                        <li>The new product line accounted for 20% of new sales.</li>
                      </ul>
                      <div className="flex items-center gap-1.5 mt-2 pt-2 border-t border-zinc-200 dark:border-zinc-800">
                        <span className="text-xs font-medium text-zinc-500">Sources:</span>
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-zinc-200/50 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400">Page 3</span>
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-zinc-200/50 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400">Page 7</span>
                      </div>
                    </div>
                  </div>
                </div>
                <div className="p-4 border-t border-zinc-200 dark:border-zinc-800">
                  <div className="flex gap-2">
                    <div className="flex-1 rounded-full border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 h-10 px-4 flex items-center">
                      <span className="text-sm text-zinc-400">Ask a follow-up...</span>
                    </div>
                    <div className="w-10 h-10 rounded-full bg-zinc-900 dark:bg-zinc-100 flex items-center justify-center">
                      <ArrowRight className="w-4 h-4 text-zinc-50 dark:text-zinc-900" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section id="features" className="py-24 bg-zinc-100 dark:bg-zinc-900/50">
          <div className="container mx-auto px-6">
            <div className="text-center mb-16 max-w-2xl mx-auto">
              <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-4">Enterprise-grade capabilities</h2>
              <p className="text-zinc-600 dark:text-zinc-400">
                Built from the ground up for accuracy, security, and performance.
              </p>
            </div>
            
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
              <FeatureCard 
                icon={<FileText className="w-5 h-5" />}
                title="Multimodal Understanding"
                description="Process PDFs, Word documents, and images. Extract text, tables, and structures perfectly."
              />
              <FeatureCard 
                icon={<Search className="w-5 h-5" />}
                title="Semantic Search"
                description="Find the exact information you need through advanced vector search and reranking."
              />
              <FeatureCard 
                icon={<MessageSquare className="w-5 h-5" />}
                title="Grounded Q&A"
                description="Get answers backed by facts. The AI only uses information present in your documents."
              />
              <FeatureCard 
                icon={<CheckCircle2 className="w-5 h-5" />}
                title="Accurate Citations"
                description="Every claim is linked back to the exact source chunk in your uploaded document."
              />
              <FeatureCard 
                icon={<Shield className="w-5 h-5" />}
                title="Secure Isolation"
                description="Your data is strictly isolated. Enterprise-grade Row Level Security keeps documents private."
              />
              <FeatureCard 
                icon={<Database className="w-5 h-5" />}
                title="Local Embeddings"
                description="Privacy-first processing. Embeddings are generated locally for maximum security."
              />
            </div>
          </div>
        </section>

        {/* How It Works Section */}
        <section id="how-it-works" className="py-32">
          <div className="container mx-auto px-6">
            <div className="text-center mb-20 max-w-2xl mx-auto">
              <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-4">How it works</h2>
              <p className="text-zinc-600 dark:text-zinc-400">
                From PDF to intelligent conversations in seconds.
              </p>
            </div>
            
            <div className="grid md:grid-cols-4 gap-12 md:gap-6 relative">
              {/* Connection line for desktop */}
              <div className="hidden md:block absolute top-10 left-12 right-12 h-px bg-zinc-200 dark:bg-zinc-800 z-0"></div>
              
              <Step 
                number="1"
                title="Upload"
                description="Upload your complex documents (PDFs, DOCX, Images)."
              />
              <Step 
                number="2"
                title="Process"
                description="DocuMind extracts text, tables, and generates local embeddings."
              />
              <Step 
                number="3"
                title="Ask"
                description="Chat with your document using natural language."
              />
              <Step 
                number="4"
                title="Verify"
                description="Get accurate answers backed by inline citations."
              />
            </div>
          </div>
        </section>

        {/* Final CTA */}
        <section className="py-24 border-t border-zinc-200 dark:border-zinc-800">
          <div className="container mx-auto px-6 text-center">
            <h2 className="text-3xl md:text-4xl font-bold tracking-tight mb-6">Ready to unlock your documents?</h2>
            <p className="text-zinc-600 dark:text-zinc-400 mb-10 max-w-xl mx-auto">
              Start asking questions and finding answers instantly. Secure, accurate, and lightning fast.
            </p>
            <Link 
              href="/signup" 
              className="inline-flex items-center justify-center bg-zinc-900 text-zinc-50 hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200 px-8 py-3.5 rounded-full text-base font-medium transition-colors"
            >
              Start using DocuMind AI
            </Link>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-200 dark:border-zinc-800 py-12 bg-zinc-50 dark:bg-zinc-950">
        <div className="container mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-zinc-900 dark:bg-zinc-100 text-zinc-50 dark:text-zinc-900 rounded flex items-center justify-center font-bold text-sm leading-none">
              D
            </div>
            <span className="font-semibold text-sm">DocuMind AI</span>
          </div>
          <p className="text-sm text-zinc-500">
            &copy; {new Date().getFullYear()} DocuMind AI. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  )
}

function FeatureCard({ icon, title, description }: { icon: React.ReactNode, title: string, description: string }) {
  return (
    <div className="p-6 rounded-2xl bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 shadow-sm hover:shadow-md transition-shadow">
      <div className="w-10 h-10 rounded-lg bg-zinc-100 dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 flex items-center justify-center mb-4">
        {icon}
      </div>
      <h3 className="font-semibold text-lg mb-2">{title}</h3>
      <p className="text-zinc-600 dark:text-zinc-400 text-sm leading-relaxed">{description}</p>
    </div>
  )
}

function Step({ number, title, description }: { number: string, title: string, description: string }) {
  return (
    <div className="relative z-10 flex flex-col items-center text-center">
      <div className="w-20 h-20 rounded-full bg-white dark:bg-zinc-950 border-4 border-zinc-50 dark:border-zinc-900 shadow-[0_0_0_1px_rgba(0,0,0,0.1)] dark:shadow-[0_0_0_1px_rgba(255,255,255,0.1)] flex items-center justify-center text-xl font-bold mb-6">
        {number}
      </div>
      <h3 className="font-semibold text-xl mb-3">{title}</h3>
      <p className="text-zinc-600 dark:text-zinc-400 text-sm">{description}</p>
    </div>
  )
}
