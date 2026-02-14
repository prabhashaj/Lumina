'use client'

import { useEffect, useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth'
import Link from 'next/link'
import {
  Sparkles,
  ArrowRight,
  Search,
  Brain,
  BookOpen,
  GraduationCap,
  Zap,
  Globe,
  MessageSquare,
  Star,
  Shield,
  Target,
  Lightbulb,
  CheckCircle2,
  Image as ImageIcon,
  FileText,
  Upload,
  BarChart3,
  Layers,
  MousePointerClick,
  ChevronDown,
  Presentation,
  Mic,
  Play,
  Volume2,
  Camera,
} from 'lucide-react'

export default function LandingPage() {
  const router = useRouter()
  const { user, isLoading } = useAuth()
  const [scrollY, setScrollY] = useState(0)
  const [visibleSections, setVisibleSections] = useState<Set<string>>(new Set())
  const sectionRefs = useRef<Map<string, HTMLElement>>(new Map())

  useEffect(() => {
    if (!isLoading && user) {
      router.push('/app')
    }
  }, [user, isLoading, router])

  useEffect(() => {
    const handleScroll = () => setScrollY(window.scrollY)
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setVisibleSections((prev) => new Set([...prev, entry.target.id]))
          }
        })
      },
      { threshold: 0.1, rootMargin: '0px 0px -50px 0px' }
    )
    sectionRefs.current.forEach((el) => observer.observe(el))
    return () => observer.disconnect()
  }, [])

  const addRef = (id: string) => (el: HTMLElement | null) => {
    if (el) sectionRefs.current.set(id, el)
  }

  const isVisible = (id: string) => visibleSections.has(id)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-[hsl(73,31%,45%)] to-[hsl(73,40%,38%)] flex items-center justify-center animate-pulse-glow">
          <Sparkles className="w-5 h-5 text-white" />
        </div>
      </div>
    )
  }

  if (user) return null

  const features = [
    {
      icon: Search,
      label: 'AI Research',
      desc: 'Deep research on any topic with cited sources, visual aids, and real-time explanations',
      color: 'hsl(73,31%,55%)',
      colorBg: 'hsl(73,31%,45%)',
    },
    {
      icon: GraduationCap,
      label: 'Exam Prep',
      desc: 'Structured study roadmaps with chapters, interactive quizzes, and progress tracking',
      color: 'hsl(270,60%,65%)',
      colorBg: 'hsl(270,50%,50%)',
    },
    {
      icon: Target,
      label: 'Personalized',
      desc: 'Adaptive learning plans with diagnostic assessments tailored to your skill level',
      color: 'hsl(35,90%,55%)',
      colorBg: 'hsl(35,80%,45%)',
    },
    {
      icon: Presentation,
      label: 'Video Lectures',
      desc: 'AI-generated whiteboard presentations with relevant images and voice narration',
      color: 'hsl(350,70%,60%)',
      colorBg: 'hsl(350,60%,48%)',
    },
    {
      icon: Camera,
      label: 'Doubt Solver',
      desc: 'Upload a photo of any problem and get step-by-step AI solutions instantly',
      color: 'hsl(190,80%,55%)',
      colorBg: 'hsl(190,70%,42%)',
    },
  ]

  return (
    <div className="min-h-screen bg-background text-foreground overflow-x-hidden">
      {/* ── Navbar ── */}
      <nav
        className={`fixed top-0 w-full z-50 transition-all duration-500 ${
          scrollY > 50
            ? 'glass border-b border-border/20 shadow-lg shadow-black/5'
            : 'bg-transparent'
        }`}
      >
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[hsl(73,31%,45%)] to-[hsl(73,40%,38%)] flex items-center justify-center shadow-lg shadow-[hsl(73,31%,45%)]/20">
              <Sparkles className="w-4.5 h-4.5 text-white" />
            </div>
            <span className="text-lg font-bold tracking-tight text-gradient">Lumina</span>
          </div>

          <div className="hidden md:flex items-center gap-8">
            <a href="#features" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Features</a>
            <a href="#research" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Research</a>
            <a href="#modes" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Modes</a>
            <a href="#lectures" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Lectures</a>
            <a href="#tools" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Doubt Solver</a>
          </div>

          <div className="flex items-center gap-3">
            <Link href="/login" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors px-4 py-2">
              Log in
            </Link>
            <Link
              href="/signup"
              className="text-sm font-semibold bg-gradient-to-r from-[hsl(73,31%,45%)] to-[hsl(73,31%,55%)] text-white px-5 py-2.5 rounded-xl hover:shadow-lg hover:shadow-[hsl(73,31%,45%)]/25 transition-all duration-300 hover:scale-[1.02]"
            >
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      {/* ── Hero Section ── */}
      <section className="relative pt-32 pb-8 overflow-hidden">
        {/* Ambient orbs */}
        <div className="orb orb-primary w-[800px] h-[800px] -top-60 -right-60 animate-float" />
        <div className="orb orb-secondary w-[500px] h-[500px] bottom-0 -left-40 animate-float" style={{ animationDelay: '1.5s' }} />
        <div className="orb w-[300px] h-[300px] top-1/3 left-1/2 animate-float" style={{ background: 'hsl(270,50%,50%)', filter: 'blur(100px)', opacity: 0.04, animationDelay: '3s' }} />

        <div className="relative z-10 max-w-5xl mx-auto px-6 text-center">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-[hsl(73,31%,45%)]/20 bg-[hsl(73,31%,45%)]/5 mb-8 animate-fadeInUp">
            <div className="w-1.5 h-1.5 rounded-full bg-[hsl(73,31%,55%)] animate-pulse" />
            <span className="text-xs font-medium text-[hsl(73,31%,55%)]">Multi-Agent AI Learning Platform</span>
          </div>

          {/* Main heading */}
          <h1 className="text-5xl sm:text-7xl lg:text-8xl font-bold tracking-tight mb-8 leading-[0.95] animate-fadeInUp" style={{ animationDelay: '0.1s' }}>
            Learn anything{' '}
            <br className="hidden sm:block" />
            <span className="text-gradient">10x faster</span> with{' '}
            <br className="hidden sm:block" />
            <span className="relative inline-block">
              Lumina
              <svg className="absolute -bottom-2 left-0 w-full h-3" viewBox="0 0 200 12" fill="none" preserveAspectRatio="none">
                <path d="M2 8 C40 2, 80 10, 120 6 C150 3, 175 8, 198 5" stroke="hsl(73,31%,55%)" strokeWidth="3" strokeLinecap="round" className="landing-underline-draw" />
              </svg>
            </span>
          </h1>

          {/* Subtitle */}
          <p className="text-lg sm:text-xl text-muted-foreground max-w-2xl mx-auto mb-12 leading-relaxed animate-fadeInUp" style={{ animationDelay: '0.2s' }}>
            Research any topic, prep for exams, get personalized learning plans, and watch AI-generated 
            video lectures — all powered by a multi-agent AI system.
          </p>

          {/* CTA buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16 animate-fadeInUp" style={{ animationDelay: '0.3s' }}>
            <Link
              href="/signup"
              className="group flex items-center gap-2.5 px-8 py-4 bg-gradient-to-r from-[hsl(73,31%,45%)] to-[hsl(73,31%,55%)] text-white font-semibold rounded-2xl hover:shadow-2xl hover:shadow-[hsl(73,31%,45%)]/30 transition-all duration-300 hover:scale-[1.03] text-base animate-glowPulse"
            >
              Start learning free
              <ArrowRight className="w-4.5 h-4.5 group-hover:translate-x-1.5 transition-transform" />
            </Link>
            <Link
              href="/login"
              className="flex items-center gap-2 px-8 py-4 border border-border/40 rounded-2xl hover:bg-card/60 transition-all duration-300 text-sm font-medium text-muted-foreground hover:text-foreground hover:border-border/60"
            >
              Sign in to your account
            </Link>
          </div>

          {/* Feature pills row */}
          <div className="flex flex-wrap items-center justify-center gap-3 mb-16 animate-fadeInUp" style={{ animationDelay: '0.4s' }}>
            {features.map((f, i) => (
              <div
                key={i}
                className="flex items-center gap-2 px-4 py-2 rounded-full border backdrop-blur-sm transition-all duration-300 hover:scale-105 cursor-default"
                style={{
                  borderColor: `${f.color}22`,
                  background: `${f.colorBg}08`,
                }}
              >
                <f.icon className="w-3.5 h-3.5" style={{ color: f.color }} />
                <span className="text-xs font-medium" style={{ color: f.color }}>{f.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Hero Screenshot */}
        <div className="relative z-10 max-w-7xl mx-auto px-6 animate-scaleIn" style={{ animationDelay: '0.3s' }}>
          <div className="relative rounded-2xl border border-border/30 overflow-hidden bg-card/80 backdrop-blur-sm shadow-2xl shadow-black/20 landing-hero-glow">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-border/20 bg-muted/30">
              <div className="flex gap-1.5">
                <div className="w-3 h-3 rounded-full bg-red-500/60" />
                <div className="w-3 h-3 rounded-full bg-yellow-500/60" />
                <div className="w-3 h-3 rounded-full bg-green-500/60" />
              </div>
              <div className="flex-1 flex justify-center">
                <div className="px-4 py-1 rounded-lg bg-muted/50 text-xs text-muted-foreground flex items-center gap-2">
                  <Shield className="w-3 h-3" />
                  lumina.app
                </div>
              </div>
            </div>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/screenshots/image1.png"
              alt="Lumina Research Mode - Ask anything and get comprehensive AI-powered answers"
              className="w-full h-auto block"
              loading="eager"
            />
          </div>
        </div>

        {/* Scroll indicator */}
        <div className="flex justify-center mt-16 animate-fadeInUp" style={{ animationDelay: '0.8s' }}>
          <a href="#features" className="flex flex-col items-center gap-2 text-muted-foreground/40 hover:text-muted-foreground/70 transition-colors">
            <span className="text-[10px] font-semibold tracking-[0.2em] uppercase">Discover more</span>
            <ChevronDown className="w-4 h-4 animate-float" />
          </a>
        </div>
      </section>

      {/* ── Features Overview ── */}
      <section
        id="features"
        ref={addRef('features')}
        className={`py-32 relative transition-all duration-1000 ${isVisible('features') ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'}`}
      >
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[hsl(73,31%,45%)]/[0.02] to-transparent" />
        <div className="max-w-7xl mx-auto px-6 relative z-10">
          <div className={`text-center mb-20 ${isVisible('features') ? 'animate-fadeInUp' : ''}`}>
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-[hsl(73,31%,45%)]/20 bg-[hsl(73,31%,45%)]/5 mb-6">
              <Sparkles className="w-3.5 h-3.5 text-[hsl(73,31%,55%)]" />
              <span className="text-xs font-medium text-[hsl(73,31%,55%)]">Why Lumina</span>
            </div>
            <h2 className="text-4xl sm:text-6xl font-bold tracking-tight mb-5">
              Five powerful ways to <span className="text-gradient">learn</span>
            </h2>
            <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
              From deep research and video lectures to instant doubt solving and personalized learning — Lumina has you covered.
            </p>
          </div>

          {/* 5 Feature Cards Grid: single row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-5 max-w-7xl mx-auto">
            {features.map((f, i) => (
              <div
                key={i}
                className="group relative p-6 rounded-2xl border border-border/20 bg-card/40 backdrop-blur-sm hover:border-border/40 transition-all duration-500 hover:-translate-y-2 hover:shadow-xl cursor-default"
                style={isVisible('features') ? { animation: `fadeInStagger 0.6s cubic-bezier(0.16,1,0.3,1) ${i * 100 + 200}ms both` } : { opacity: 0 }}
              >
                {/* Glow on hover */}
                <div
                  className="absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                  style={{ background: `radial-gradient(ellipse at center, ${f.colorBg}10 0%, transparent 70%)` }}
                />
                <div className="relative z-10">
                  <div
                    className="w-12 h-12 rounded-xl flex items-center justify-center mb-5 transition-all duration-300 group-hover:scale-110 group-hover:shadow-lg"
                    style={{
                      background: `${f.colorBg}12`,
                      border: `1px solid ${f.color}22`,
                    }}
                  >
                    <f.icon className="w-5.5 h-5.5" style={{ color: f.color }} />
                  </div>
                  <h3 className="text-lg font-bold mb-2 tracking-tight">{f.label}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Research Mode Deep Dive ── */}
      <section
        id="research"
        ref={addRef('research')}
        className={`py-32 relative transition-all duration-1000 ${isVisible('research') ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'}`}
      >
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[hsl(73,31%,45%)]/[0.03] to-transparent" />
        <div className="orb orb-secondary w-[350px] h-[350px] top-40 -right-20 animate-float" style={{ animationDelay: '1s' }} />
        <div className="max-w-7xl mx-auto px-6 relative z-10">
          <div className={`text-center mb-16 ${isVisible('research') ? 'animate-fadeInUp' : ''}`}>
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-[hsl(73,31%,45%)]/20 bg-[hsl(73,31%,45%)]/5 mb-6">
              <Zap className="w-3.5 h-3.5 text-[hsl(73,31%,55%)]" />
              <span className="text-xs font-medium text-[hsl(73,31%,55%)]">Research Mode</span>
            </div>
            <h2 className="text-4xl sm:text-6xl font-bold tracking-tight mb-5">
              Ask anything, get a <span className="text-gradient">complete lesson</span>
            </h2>
            <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
              Every response includes TL;DR, detailed explanations, analogies, visual aids, practice questions, and cited sources — all generated in real-time.
            </p>
          </div>

          {/* Scrollable Research Screenshot */}
          <div className="max-w-4xl mx-auto">
            <div className="relative rounded-2xl border border-border/30 overflow-hidden bg-card/80 backdrop-blur-sm shadow-2xl">
              <div className="flex items-center justify-between px-4 py-3 border-b border-border/20 bg-muted/30">
                <div className="flex gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-red-500/60" />
                  <div className="w-3 h-3 rounded-full bg-yellow-500/60" />
                  <div className="w-3 h-3 rounded-full bg-green-500/60" />
                </div>
                <div className="px-4 py-1 rounded-lg bg-muted/50 text-xs text-muted-foreground flex items-center gap-2">
                  <Shield className="w-3 h-3" />
                  lumina.app/research
                </div>
                <div className="flex items-center gap-1.5 text-muted-foreground/50">
                  <MousePointerClick className="w-3.5 h-3.5" />
                  <span className="text-[10px]">Scroll to explore</span>
                </div>
              </div>
              <div style={{ height: '600px', overflowY: 'scroll' }} className="screenshot-scroll-container">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src="/screenshots/lumina4.png"
                  alt="Full research response showing TL;DR, explanations, visual aids, analogies, practice questions, and sources"
                  className="w-full h-auto block"
                  loading="lazy"
                />
              </div>
            </div>
            <p className="text-center text-xs text-muted-foreground/50 mt-4 flex items-center justify-center gap-1.5">
              <MousePointerClick className="w-3 h-3" />
              Scroll inside the preview to see the full research response
            </p>
          </div>

          {/* Feature highlights below screenshot */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mt-16 max-w-4xl mx-auto">
            {[
              { icon: Zap, label: 'TL;DR Summary', desc: 'Quick overview first' },
              { icon: BookOpen, label: 'Deep Explanation', desc: 'Structured sections' },
              { icon: Lightbulb, label: 'Real-World Analogy', desc: 'Concepts that click' },
              { icon: Globe, label: 'Cited Sources', desc: 'Verified references' },
            ].map((item, i) => (
              <div key={i} className="text-center group" style={isVisible('research') ? { animation: `fadeInStagger 0.5s cubic-bezier(0.16,1,0.3,1) ${i * 100 + 300}ms both` } : { opacity: 0 }}>
                <div className="w-12 h-12 rounded-xl bg-card border border-border/30 flex items-center justify-center mx-auto mb-3 group-hover:border-[hsl(73,31%,45%)]/40 group-hover:bg-[hsl(73,31%,45%)]/5 transition-all duration-300 group-hover:scale-110">
                  <item.icon className="w-5 h-5 text-[hsl(73,31%,55%)] group-hover:scale-110 transition-transform" />
                </div>
                <p className="text-sm font-semibold mb-1">{item.label}</p>
                <p className="text-xs text-muted-foreground">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Visual Explanations & Sources ── */}
      <section
        id="visuals"
        ref={addRef('visuals')}
        className={`py-32 transition-all duration-1000 ${isVisible('visuals') ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'}`}
      >
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-start">
            {/* Visual Explanations */}
            <div className={isVisible('visuals') ? 'animate-slideInLeft' : ''} style={{ animationDelay: '0.1s' }}>
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-[hsl(200,60%,50%)]/20 bg-[hsl(200,60%,50%)]/5 mb-6">
                <ImageIcon className="w-3.5 h-3.5 text-[hsl(200,60%,50%)]" />
                <span className="text-xs font-medium text-[hsl(200,60%,50%)]">Visual Learning</span>
              </div>
              <h3 className="text-3xl font-bold tracking-tight mb-4">
                Images &amp; diagrams <span className="text-gradient">found for you</span>
              </h3>
              <p className="text-muted-foreground mb-8 leading-relaxed">
                Lumina automatically discovers and includes relevant visual explanations from across the web — diagrams, infographics, and illustrations that make complex topics easier to grasp.
              </p>
              <div className="rounded-2xl border border-border/30 overflow-hidden shadow-xl group/img hover:shadow-2xl hover:shadow-[hsl(200,60%,50%)]/10 transition-all duration-500 hover:-translate-y-1">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src="/screenshots/image4.png"
                  alt="Visual explanations with diagrams and images automatically found by Lumina"
                  className="w-full h-auto block transition-transform duration-700 group-hover/img:scale-[1.02]"
                  loading="lazy"
                />
              </div>
            </div>

            {/* Sources */}
            <div className={isVisible('visuals') ? 'animate-slideInRight-lg' : ''} style={{ animationDelay: '0.25s' }}>
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-emerald-500/20 bg-emerald-500/5 mb-6">
                <Globe className="w-3.5 h-3.5 text-emerald-500" />
                <span className="text-xs font-medium text-emerald-500">Verified Sources</span>
              </div>
              <h3 className="text-3xl font-bold tracking-tight mb-4">
                Every claim is <span className="text-gradient">backed by sources</span>
              </h3>
              <p className="text-muted-foreground mb-8 leading-relaxed">
                No hallucinations. Every factual claim is backed by real, clickable sources from the web. Lumina cites its references so you can verify and explore further.
              </p>
              <div className="rounded-2xl border border-border/30 overflow-hidden shadow-xl group/img hover:shadow-2xl hover:shadow-emerald-500/10 transition-all duration-500 hover:-translate-y-1">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src="/screenshots/image5.png"
                  alt="Source citations with numbered references from verified websites"
                  className="w-full h-auto block transition-transform duration-700 group-hover/img:scale-[1.02]"
                  loading="lazy"
                />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Learning Modes Section ── */}
      <section
        id="modes"
        ref={addRef('modes')}
        className={`py-32 relative transition-all duration-1000 ${isVisible('modes') ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'}`}
      >
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[hsl(73,31%,45%)]/[0.03] to-transparent" />
        <div className="orb orb-primary w-[500px] h-[500px] top-1/3 -left-40 animate-float" />
        <div className="max-w-7xl mx-auto px-6 relative z-10">
          <div className={`text-center mb-20 ${isVisible('modes') ? 'animate-fadeInUp' : ''}`}>
            <h2 className="text-4xl sm:text-6xl font-bold tracking-tight mb-5">
              Powerful <span className="text-gradient">learning modes</span>
            </h2>
            <p className="text-muted-foreground text-lg max-w-xl mx-auto">
              Whether you&apos;re preparing for exams or building skills — Lumina adapts to your learning style
            </p>
          </div>

          {/* Mode 1: Exam Prep */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center mb-32">
            <div className="order-2 lg:order-1">
              <div className="relative rounded-2xl border border-border/30 overflow-hidden bg-card/80 shadow-2xl">
                <div className="flex items-center justify-between px-4 py-3 border-b border-border/20 bg-muted/30">
                  <div className="flex gap-1.5">
                    <div className="w-3 h-3 rounded-full bg-red-500/60" />
                    <div className="w-3 h-3 rounded-full bg-yellow-500/60" />
                    <div className="w-3 h-3 rounded-full bg-green-500/60" />
                  </div>
                  <div className="px-3 py-1 rounded-lg bg-purple-500/10 text-xs text-purple-400 font-medium flex items-center gap-1.5">
                    <GraduationCap className="w-3 h-3" />
                    Exam Prep Mode
                  </div>
                  <div className="flex items-center gap-1.5 text-muted-foreground/50">
                    <MousePointerClick className="w-3.5 h-3.5" />
                    <span className="text-[10px]">Scroll</span>
                  </div>
                </div>
                <div style={{ height: '500px', overflowY: 'scroll' }} className="screenshot-scroll-container">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src="/screenshots/lumina3.png"
                    alt="Exam Prep mode showing Machine Learning roadmap with chapters, topics, quizzes, and progress tracking"
                    className="w-full h-auto block"
                    loading="lazy"
                  />
                </div>
              </div>
            </div>

            <div className="order-1 lg:order-2">
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-purple-500/20 bg-purple-500/5 mb-6">
                <GraduationCap className="w-3.5 h-3.5 text-purple-400" />
                <span className="text-xs font-medium text-purple-400">Exam Prep Mode</span>
              </div>
              <h3 className="text-3xl sm:text-4xl font-bold tracking-tight mb-5">
                Structured roadmaps for <span className="text-gradient">exam success</span>
              </h3>
              <p className="text-muted-foreground leading-relaxed mb-8">
                Enter any subject — Machine Learning, Physics, History — and Lumina generates a complete study roadmap with chapters, topics, and interactive quizzes. Track your progress and learn systematically.
              </p>
              <div className="space-y-4">
                {[
                  { icon: Layers, text: 'Auto-generated chapter & topic structure' },
                  { icon: FileText, text: 'AI-powered content for each topic' },
                  { icon: CheckCircle2, text: 'Interactive quizzes with scoring' },
                  { icon: BarChart3, text: 'Progress tracking across topics' },
                ].map((item, i) => (
                  <div key={i} className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-lg bg-purple-500/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                      <item.icon className="w-4 h-4 text-purple-400" />
                    </div>
                    <span className="text-muted-foreground text-sm leading-relaxed">{item.text}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Mode 2: Personalized Learning */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-amber-500/20 bg-amber-500/5 mb-6">
                <Target className="w-3.5 h-3.5 text-amber-500" />
                <span className="text-xs font-medium text-amber-500">Personalized Mode</span>
              </div>
              <h3 className="text-3xl sm:text-4xl font-bold tracking-tight mb-5">
                Learning plans <span className="text-gradient">tailored to you</span>
              </h3>
              <p className="text-muted-foreground leading-relaxed mb-8">
                Take a diagnostic assessment, and Lumina identifies your strengths, weaknesses, and skill level. Then it creates a custom multi-phase learning journey with estimated times, personalized tips, and adaptive content.
              </p>
              <div className="space-y-4">
                {[
                  { icon: Brain, text: 'Diagnostic assessment to gauge your level' },
                  { icon: Star, text: 'Identifies strengths & focus areas' },
                  { icon: Target, text: 'Multi-phase learning journey with milestones' },
                  { icon: Lightbulb, text: 'Personalized tips based on your learning style' },
                ].map((item, i) => (
                  <div key={i} className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-lg bg-amber-500/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                      <item.icon className="w-4 h-4 text-amber-500" />
                    </div>
                    <span className="text-muted-foreground text-sm leading-relaxed">{item.text}</span>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <div className="relative rounded-2xl border border-border/30 overflow-hidden bg-card/80 shadow-2xl">
                <div className="flex items-center justify-between px-4 py-3 border-b border-border/20 bg-muted/30">
                  <div className="flex gap-1.5">
                    <div className="w-3 h-3 rounded-full bg-red-500/60" />
                    <div className="w-3 h-3 rounded-full bg-yellow-500/60" />
                    <div className="w-3 h-3 rounded-full bg-green-500/60" />
                  </div>
                  <div className="px-3 py-1 rounded-lg bg-amber-500/10 text-xs text-amber-500 font-medium flex items-center gap-1.5">
                    <Target className="w-3 h-3" />
                    Personalized Mode
                  </div>
                  <div className="flex items-center gap-1.5 text-muted-foreground/50">
                    <MousePointerClick className="w-3.5 h-3.5" />
                    <span className="text-[10px]">Scroll</span>
                  </div>
                </div>
                <div style={{ height: '500px', overflowY: 'scroll' }} className="screenshot-scroll-container">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src="/screenshots/lumina2.png"
                    alt="Personalized learning plan with assessment score, learning phases, strengths, focus areas, and personalized tips"
                    className="w-full h-auto block"
                    loading="lazy"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Video Lectures Section ── */}
      <section
        id="lectures"
        ref={addRef('lectures')}
        className={`py-32 relative transition-all duration-1000 ${isVisible('lectures') ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'}`}
      >
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[hsl(350,60%,48%)]/[0.03] to-transparent" />
        <div className="orb w-[500px] h-[500px] top-20 -right-40 animate-float" style={{ background: 'hsl(350,60%,50%)', filter: 'blur(100px)', opacity: 0.06, animationDelay: '2s' }} />
        <div className="orb orb-primary w-[300px] h-[300px] bottom-20 -left-20 animate-float" style={{ animationDelay: '0.5s' }} />

        <div className="max-w-6xl mx-auto px-6 relative z-10">
          {/* Heading & subtitle — centered */}
          <div className={`text-center mb-16 ${isVisible('lectures') ? 'animate-fadeInUp' : ''}`}>
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-rose-500/20 bg-rose-500/5 mb-6">
              <Presentation className="w-3.5 h-3.5 text-rose-400" />
              <span className="text-xs font-medium text-rose-400">Video Lecture Mode</span>
              <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-rose-500/15 text-rose-400 uppercase tracking-wider">New</span>
            </div>
            <h2 className="text-4xl sm:text-6xl font-bold tracking-tight mb-5">
              AI-generated <span className="text-gradient">whiteboard lectures</span>
            </h2>
            <p className="text-muted-foreground text-lg max-w-2xl mx-auto leading-relaxed">
              Enter any topic and Lumina generates a full slide presentation with a whiteboard-style design, auto-fetched relevant images, and natural AI narration — like having a personal teacher explain concepts to you.
            </p>
          </div>

          {/* Full-width screenshot */}
          <div className={`relative mb-16 ${isVisible('lectures') ? 'animate-scaleIn' : ''}`} style={{ animationDelay: '0.15s' }}>
            <div className="relative rounded-2xl border border-border/30 overflow-hidden bg-card/80 shadow-2xl hover:shadow-rose-500/10 transition-all duration-500 group/lecture landing-hero-glow">
              <div className="flex items-center justify-between px-4 py-3 border-b border-border/20 bg-muted/30">
                <div className="flex gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-red-500/60" />
                  <div className="w-3 h-3 rounded-full bg-yellow-500/60" />
                  <div className="w-3 h-3 rounded-full bg-green-500/60" />
                </div>
                <div className="px-3 py-1 rounded-lg bg-rose-500/10 text-xs text-rose-400 font-medium flex items-center gap-1.5">
                  <Presentation className="w-3 h-3" />
                  Video Lecture Mode
                </div>
                <div className="flex items-center gap-1.5 text-muted-foreground/50">
                  <Volume2 className="w-3.5 h-3.5" />
                  <span className="text-[10px]">AI Narration</span>
                </div>
              </div>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src="/screenshots/lumina5.png"
                alt="AI Video Lecture showing whiteboard-style slide with neurons diagram, bullet points, and AI narration panel"
                className="w-full h-auto block transition-transform duration-700 group-hover/lecture:scale-[1.01]"
                loading="lazy"
              />
            </div>

            {/* Floating feature badges */}
            <div className="hidden lg:block">
              <div
                className="absolute -right-4 top-1/3 px-3 py-2 rounded-xl bg-card/90 backdrop-blur-xl border border-border/30 shadow-lg flex items-center gap-2 text-xs"
                style={isVisible('lectures') ? { animation: 'fadeInStagger 0.6s cubic-bezier(0.16,1,0.3,1) 500ms both' } : { opacity: 0 }}
              >
                <div className="w-6 h-6 rounded-lg bg-rose-500/15 flex items-center justify-center">
                  <Mic className="w-3 h-3 text-rose-400" />
                </div>
                <span className="text-muted-foreground font-medium">AI Narration</span>
              </div>
              <div
                className="absolute -left-4 bottom-1/3 px-3 py-2 rounded-xl bg-card/90 backdrop-blur-xl border border-border/30 shadow-lg flex items-center gap-2 text-xs"
                style={isVisible('lectures') ? { animation: 'fadeInStagger 0.6s cubic-bezier(0.16,1,0.3,1) 700ms both' } : { opacity: 0 }}
              >
                <div className="w-6 h-6 rounded-lg bg-emerald-500/15 flex items-center justify-center">
                  <ImageIcon className="w-3 h-3 text-emerald-400" />
                </div>
                <span className="text-muted-foreground font-medium">Auto Images</span>
              </div>
            </div>
          </div>

          {/* Feature bullets — grid below the image */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-6 max-w-5xl mx-auto mb-12">
            {[
              { icon: Layers, text: 'Auto-generated slide decks with multiple layouts' },
              { icon: ImageIcon, text: 'Relevant images fetched automatically per slide' },
              { icon: Mic, text: 'Natural AI voice narration with word highlighting' },
              { icon: Play, text: 'Auto-advance with continuous playback' },
              { icon: Volume2, text: 'Conversational teacher-style explanations' },
            ].map((item, i) => (
              <div
                key={i}
                className="flex flex-col items-center text-center gap-3 p-5 rounded-2xl border border-border/15 bg-card/30 backdrop-blur-sm hover:border-rose-500/20 hover:bg-rose-500/[0.03] transition-all duration-300 group"
                style={isVisible('lectures') ? { animation: `fadeInStagger 0.5s cubic-bezier(0.16,1,0.3,1) ${i * 80 + 400}ms both` } : { opacity: 0 }}
              >
                <div className="w-10 h-10 rounded-xl bg-rose-500/10 flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                  <item.icon className="w-4.5 h-4.5 text-rose-400" />
                </div>
                <span className="text-muted-foreground text-xs leading-relaxed">{item.text}</span>
              </div>
            ))}
          </div>

          {/* CTA */}
          <div className="text-center">
            <Link
              href="/signup"
              className="group inline-flex items-center gap-2.5 px-8 py-4 bg-gradient-to-r from-rose-500 to-rose-600 text-white font-semibold rounded-2xl hover:shadow-2xl hover:shadow-rose-500/25 transition-all duration-300 hover:scale-[1.03] text-base"
            >
              Try Video Lectures
              <ArrowRight className="w-4.5 h-4.5 group-hover:translate-x-1.5 transition-transform" />
            </Link>
          </div>
        </div>
      </section>

      {/* ── Doubt Solver Section ── */}
      <section
        id="tools"
        ref={addRef('tools')}
        className={`py-32 relative transition-all duration-1000 ${isVisible('tools') ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'}`}
      >
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[hsl(190,70%,42%)]/[0.02] to-transparent" />
        <div className="orb w-[400px] h-[400px] top-20 -left-40 animate-float" style={{ background: 'hsl(190,70%,50%)', filter: 'blur(100px)', opacity: 0.05, animationDelay: '1s' }} />
        <div className="orb w-[300px] h-[300px] bottom-40 -right-20 animate-float" style={{ background: 'hsl(260,50%,55%)', filter: 'blur(100px)', opacity: 0.04, animationDelay: '2.5s' }} />

        <div className="max-w-7xl mx-auto px-6 relative z-10">
          <div className={`text-center mb-20 ${isVisible('tools') ? 'animate-fadeInUp' : ''}`}>
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-cyan-500/20 bg-cyan-500/5 mb-6">
              <Zap className="w-3.5 h-3.5 text-cyan-400" />
              <span className="text-xs font-medium text-cyan-400">Learning Tools</span>
              <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-cyan-500/15 text-cyan-400 uppercase tracking-wider">New</span>
            </div>
            <h2 className="text-4xl sm:text-6xl font-bold tracking-tight mb-5">
              Instant <span className="text-gradient">doubt solving</span>
            </h2>
            <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
              Stuck on a tough question? Snap a photo and get instant AI-powered solutions.
            </p>
          </div>

          {/* Doubt Solver */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-cyan-500/20 bg-cyan-500/5 mb-6">
                <Camera className="w-3.5 h-3.5 text-cyan-400" />
                <span className="text-xs font-medium text-cyan-400">AI Doubt Solver</span>
              </div>
              <h3 className="text-3xl sm:text-4xl font-bold tracking-tight mb-5">
                Snap a photo, get <span className="text-gradient">instant answers</span>
              </h3>
              <p className="text-muted-foreground leading-relaxed mb-8">
                Stuck on a math problem, circuit diagram, or chemistry equation? Simply upload a photo or take a picture, and Lumina&apos;s AI vision reads the question and provides a detailed, step-by-step solution.
              </p>
              <div className="space-y-4">
                {[
                  { icon: Upload, text: 'Drag-and-drop or camera capture for instant upload' },
                  { icon: Search, text: 'AI Vision reads text, equations, diagrams from images' },
                  { icon: Lightbulb, text: 'Step-by-step solutions with clear explanations' },
                  { icon: MessageSquare, text: 'Add optional context or specific questions' },
                ].map((item, i) => (
                  <div key={i} className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-lg bg-cyan-500/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                      <item.icon className="w-4 h-4 text-cyan-400" />
                    </div>
                    <span className="text-muted-foreground text-sm leading-relaxed">{item.text}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className={isVisible('tools') ? 'animate-scaleIn' : ''} style={{ animationDelay: '0.15s' }}>
              <div className="relative rounded-2xl border border-border/30 overflow-hidden bg-card/80 shadow-2xl hover:shadow-cyan-500/10 transition-all duration-500 group/doubt">
                <div className="flex items-center justify-between px-4 py-3 border-b border-border/20 bg-muted/30">
                  <div className="flex gap-1.5">
                    <div className="w-3 h-3 rounded-full bg-red-500/60" />
                    <div className="w-3 h-3 rounded-full bg-yellow-500/60" />
                    <div className="w-3 h-3 rounded-full bg-green-500/60" />
                  </div>
                  <div className="px-3 py-1 rounded-lg bg-cyan-500/10 text-xs text-cyan-400 font-medium flex items-center gap-1.5">
                    <Camera className="w-3 h-3" />
                    Doubt Solver
                  </div>
                  <div className="w-16" />
                </div>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src="/screenshots/lumina6.png"
                  alt="Doubt Solver mode showing image upload with calculus problem and AI-powered solution"
                  className="w-full h-auto block transition-transform duration-700 group-hover/doubt:scale-[1.01]"
                  loading="lazy"
                />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── CTA Section ── */}
      <section
        id="cta"
        ref={addRef('cta')}
        className="py-32 relative overflow-hidden"
      >
        <div className="absolute inset-0 bg-gradient-to-t from-[hsl(73,31%,45%)]/[0.04] via-transparent to-transparent" />
        <div className="orb orb-primary w-[600px] h-[600px] top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" style={{ opacity: 0.06 }} />
        <div className="orb orb-secondary w-[300px] h-[300px] bottom-10 -right-20" style={{ opacity: 0.04 }} />

        <div className={`max-w-3xl mx-auto px-6 text-center relative z-10 transition-all duration-1000 ${isVisible('cta') ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'}`}>
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-[hsl(73,31%,45%)]/20 bg-[hsl(73,31%,45%)]/5 mb-8">
            <Sparkles className="w-3.5 h-3.5 text-[hsl(73,31%,55%)]" />
            <span className="text-xs font-medium text-[hsl(73,31%,55%)]">Free to get started</span>
          </div>
          <h2 className="text-4xl sm:text-6xl lg:text-7xl font-bold tracking-tight mb-6">
            Start learning with <span className="text-gradient">Lumina</span>
          </h2>
          <p className="text-muted-foreground text-lg sm:text-xl mb-12 max-w-xl mx-auto leading-relaxed">
            Research any topic, prepare for exams, get personalized learning, and watch AI video lectures — all powered by a multi-agent AI system.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/signup"
              className="group flex items-center gap-2 px-10 py-5 bg-gradient-to-r from-[hsl(73,31%,45%)] to-[hsl(73,31%,55%)] text-white font-semibold rounded-2xl hover:shadow-2xl hover:shadow-[hsl(73,31%,45%)]/30 transition-all duration-300 hover:scale-[1.04] text-lg animate-glowPulse"
            >
              Get started free
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1.5 transition-transform" />
            </Link>
            <Link
              href="/login"
              className="flex items-center gap-2 px-8 py-5 border border-border/40 rounded-2xl hover:bg-card/60 transition-all duration-300 text-sm font-medium text-muted-foreground hover:text-foreground hover:border-border/60"
            >
              Sign in to your account
            </Link>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-border/20 py-12">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-[hsl(73,31%,45%)] to-[hsl(73,40%,38%)] flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-white" />
              </div>
              <span className="font-bold text-gradient">Lumina</span>
              <span className="text-xs text-muted-foreground ml-2">AI-powered research &amp; learning platform</span>
            </div>
            <p className="text-xs text-muted-foreground">&copy; {new Date().getFullYear()} Lumina. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
