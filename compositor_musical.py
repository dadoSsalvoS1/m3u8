import os

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def estimate_syllables(text):
    """
    Estimativa simples de sílabas baseada em grupos de vogais.
    Não é perfeita gramaticalmente, mas serve como guia rítmico.
    """
    if not text:
        return 0
    vowels = "aeiouyáéíóúâêîôûãõà"
    text = text.lower()
    count = 0
    prev_is_vowel = False
    for char in text:
        if char in vowels:
            if not prev_is_vowel:
                count += 1
            prev_is_vowel = True
        else:
            prev_is_vowel = False
    return max(1, count)

class Section:
    def __init__(self, name, bars, lyrics=""):
        self.name = name
        self.bars = bars
        self.lyrics = lyrics

    def duration(self, bpm):
        # Assumindo 4/4
        return (self.bars * 4) / bpm * 60

class Song:
    def __init__(self, title, bpm):
        self.title = title
        self.bpm = bpm
        self.melody_idea = ""
        self.sections = []

    def add_section(self, section):
        self.sections.append(section)

    def current_duration(self):
        return sum(s.duration(self.bpm) for s in self.sections)

def print_separator():
    print("-" * 50)

def main():
    clear_screen()
    print("🎵 Bem-vindo ao Assistente de Composição Musical 🎵")
    print("Este assistente guiará você pelos 7 passos para criar um hit 'chiclete'.")
    print_separator()

    # Configuração Inicial
    title = input("Nome da Música (provisório): ").strip()
    if not title:
        title = "Sem Título"

    while True:
        try:
            bpm_input = input("Defina o BPM (ex: 120): ").strip()
            if not bpm_input:
                bpm = 120
            else:
                bpm = int(bpm_input)
            break
        except ValueError:
            print("Por favor, insira um número válido.")

    song = Song(title, bpm)
    print(f"\nMúsica '{song.title}' iniciada a {song.bpm} BPM.")
    print_separator()

    # Passo 1: Melodia
    print("\n🎹 PASSO 1: MELODIA FORTE")
    print("Por que: A melodia é o gancho principal. Comece por ela!")
    print("Dica: Construa uma sequência de notas que cresça em intensidade.")
    song.melody_idea = input("Descreva sua ideia de melodia ou progressão de acordes principal:\n> ")
    print("Ótimo! Mantenha essa melodia em mente (ou gravada no celular).")

    # Loop de Estrutura (Passos 5, 6, 2, 3)
    print("\n🏗️  VAMOS CONSTRUIR A ESTRUTURA")
    print("Lembre-se do Passo 5: Mantenha a estrutura simples (3 ou 4 partes principais).")
    print("Padrão sugerido: Verso -> Pré-Refrão -> Refrão -> Verso -> Refrão -> Ponte -> Refrão")

    chorus_count = 0

    while True:
        current_time = song.current_duration()
        print_separator()
        print(f"Tempo atual da música: {int(current_time // 60)}:{int(current_time % 60):02d}")

        print("\nAdicionar Seção:")
        print("1. Intro")
        print("2. Verso (Estrofe)")
        print("3. Pré-Refrão")
        print("4. Refrão (Hook)")
        print("5. Ponte")
        print("6. Outro")
        print("7. Finalizar Música e Exportar")

        choice = input("Escolha uma opção (1-7): ").strip()

        if choice == '7':
            break

        section_map = {
            '1': "Intro",
            '2': "Verso",
            '3': "Pré-Refrão",
            '4': "Refrão",
            '5': "Ponte",
            '6': "Outro"
        }

        if choice not in section_map:
            print("Opção inválida.")
            continue

        section_name = section_map[choice]

        # Input de compassos
        while True:
            try:
                bars = int(input(f"Quantos compassos terá o {section_name}? (Padrão: 4 ou 8): "))
                break
            except ValueError:
                print("Insira um número inteiro.")

        # Passo 6: Verificação de tempo do Refrão
        new_section_duration = (bars * 4) / bpm * 60
        start_time = current_time

        if section_name == "Refrão":
            chorus_count += 1
            if chorus_count == 1:
                if start_time > 50:
                    print("\n⚠️  ALERTA (PASSO 6): O Refrão está começando tarde!")
                    print(f"O refrão começa aos {int(start_time)}s. O ideal é até 40-50s.")
                    print("Considere encurtar as seções anteriores ou aumentar o BPM.")
                    confirm = input("Deseja continuar mesmo assim? (s/n): ").lower()
                    if confirm == 'n':
                        continue
                else:
                    print("\n✅ Ótimo! O refrão entra cedo (antes dos 50s). Ponto para o hit!")

        # Passo 2 & 3: Letra e Espelhamento
        print(f"\n📝 Escrevendo Letra para: {section_name}")
        print("Dica Passo 2: Ajuste a letra à melodia. Não quebre o fluxo.")
        print("Dica Passo 3: Use espelhamento (rimas e métricas repetidas).")

        lyrics_lines = []
        print("Digite a letra linha por linha (Enter vazio para terminar a seção):")
        while True:
            line = input("> ")
            if not line:
                break
            syllables = estimate_syllables(line)
            print(f"   (aprox. {syllables} sílabas sonoras)")
            lyrics_lines.append(line)

            # Checagem simples de espelhamento (comparar com linha anterior)
            if len(lyrics_lines) > 1:
                prev_syllables = estimate_syllables(lyrics_lines[-2])
                diff = abs(prev_syllables - syllables)
                if diff <= 2:
                    print("   ✨ Boa simetria rítmica com a linha anterior!")
                else:
                    print("   💡 A métrica está bem diferente da anterior. Intencional?")

        lyrics_text = "\n".join(lyrics_lines)
        song.add_section(Section(section_name, bars, lyrics_text))

        # Dica Passo 4: Reaproveitamento
        if len(song.sections) > 2:
            print("\n💡 Dica Passo 4: Você está reaproveitando ideias musicais de seções anteriores?")

    # Finalização
    print_separator()
    print("🎉 Música Finalizada!")

    # Passo 7: Clareza
    print("\n🔍 REVISÃO FINAL (Passo 7)")
    print("As letras estão claras e acessíveis? Temas universais funcionam melhor.")

    # Sanitize filename
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '_', '-')).strip()
    safe_title = safe_title.replace(' ', '_')
    if not safe_title:
        safe_title = "Minha_Musica"
    output_filename = f"{safe_title}.txt"

    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(f"TÍTULO: {song.title}\n")
        f.write(f"BPM: {song.bpm}\n")
        f.write(f"MELODIA/HOOK: {song.melody_idea}\n")
        f.write("-" * 30 + "\n\n")

        total_time = 0
        for i, section in enumerate(song.sections):
            duration = section.duration(song.bpm)
            start_min = int(total_time // 60)
            start_sec = int(total_time % 60)

            f.write(f"[{start_min}:{start_sec:02d}] {section.name.upper()} ({section.bars} compassos)\n")
            if section.lyrics:
                f.write(section.lyrics + "\n")
            else:
                f.write("(Instrumental / Sem letra definida)\n")
            f.write("\n")

            total_time += duration

        f.write("-" * 30 + "\n")
        f.write(f"DURAÇÃO TOTAL: {int(total_time // 60)}:{int(total_time % 60):02d}\n")

        # Checklist Summary in file
        f.write("\nCHECKLIST DE SUCESSO APLICADO:\n")
        f.write("[x] 1. Melodia forte definida\n")
        f.write("[x] 2. Letra ajustada à melodia\n")
        f.write("[?] 3. Espelhamento de frases (verificado pelo usuário)\n")
        f.write("[?] 4. Ideias reaproveitadas\n")
        f.write("[x] 5. Estrutura definida\n")
        if any(s.name == "Refrão" for s in song.sections):
            # Recalculate first chorus time roughly
            t = 0
            chorus_time = -1
            for s in song.sections:
                if s.name == "Refrão":
                    chorus_time = t
                    break
                t += s.duration(song.bpm)

            if chorus_time != -1 and chorus_time <= 50:
                f.write(f"[x] 6. Refrão cedo ({int(chorus_time)}s)\n")
            else:
                f.write(f"[ ] 6. Refrão cedo (Iniciou aos {int(chorus_time)}s)\n")
        else:
             f.write("[ ] 6. Refrão cedo (Sem refrão)\n")
        f.write("[?] 7. Letras claras e acessíveis\n")

    print(f"\n📄 Roteiro da música salvo em: {output_filename}")
    print("Agora é só gravar!")

if __name__ == "__main__":
    main()
