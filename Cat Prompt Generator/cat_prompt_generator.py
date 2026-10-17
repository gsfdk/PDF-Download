import random


class CatPromptGenerator:
    def __init__(self):
        self.scenarios = [
            "plotting world domination",
            "auditioning for a heist movie",
            "discovering their reflection for the first time",
            "attempting to fit in a box way too small",
            "hosting a serious business meeting",
            "training as a ninja assassin",
            "competing in the Olympics",
            "running for president",
            "judging a talent show",
            "opening a bakery",
            "practicing their comedy routine",
            "appearing on a talk show",
            "being a detective solving a mystery",
            "operating a surveillance operation",
            "trying to become a fashion influencer",
            "rehearsing for a Broadway musical",
            "running a successful startup",
            "auditioning for a superhero movie",
            "hosting a cooking show",
            "working as a stock broker",
            "performing a complex magic trick",
            "attempting parkour on furniture",
            "giving motivational speeches",
            "practicing martial arts",
            "being a professional cat burglar",
            "running a gym class",
            "launching their music career",
            "competing in a spelling bee",
            "operating a beauty salon",
            "being a movie critic",
            "teaching a university lecture",
            "working as a wedding planner",
            "perfecting their stand-up comedy",
        ]

        self.obstacles = [
            "but keeps getting distracted by a red dot",
            "but trips over their own tail",
            "but gets stuck in a cardboard box",
            "but mistakes a cucumber for a snake",
            "but forgets what they were doing mid-action",
            "but attacks their own shadow",
            "but gets defeated by a string",
            "but falls asleep unexpectedly",
            "but gets startled by their own reflection",
            "but becomes distracted by a dust particle",
            "but keeps knocking things off the table",
            "but zooms around uncontrollably",
            "but gets tangled in a blanket",
            "but becomes visibly offended by something minor",
            "but keeps meowing over the entire soundtrack",
            "but refuses to cooperate on cue",
            "but can't stop pouncing on the camera",
            "but insists on sitting on the script",
            "but keeps licking their paw mid-scene",
            "but gets spooked by a fly",
            "but demands treats every five minutes",
            "but hisses at imaginary enemies",
            "but judges everyone silently with dead eyes",
            "but keeps running off set",
        ]

        self.emotions = [
            "confidently",
            "dramatically",
            "very seriously",
            "reluctantly",
            "with extreme overconfidence",
            "while being completely confused",
            "in absolute chaos",
            "as if they totally own the place",
            "very passive-aggressively",
            "in complete denial of failure",
            "with zero effort or care",
            "like it's the most important moment of their life",
            "as if they have no idea what's happening",
            "with surprising professionalism",
            "while slowly losing their mind",
            "like they're auditioning for the Oscars",
            "with maximum sass and attitude",
            "with absolutely no regard for rules",
            "as a tiny, furry tyrant",
            "like they're too cool for this",
        ]

        self.prompt_styles = ["standard", "dramatic", "quirky", "noir"]

    def generate_prompt(self, style=None):
        """Generate a random funny cat video prompt with optional style"""
        if style is None:
            style = random.choice(self.prompt_styles)

        scenario = random.choice(self.scenarios)
        obstacle = random.choice(self.obstacles)
        emotion = random.choice(self.emotions)

        if style == "standard":
            prompt = f"A cat {emotion} {scenario} {obstacle}."
        elif style == "dramatic":
            prompt = f"🎬 DRAMATIC SCENE: Picture a feline, {emotion}, absolutely {scenario}. The twist? {obstacle[4:].capitalize()}."
        elif style == "quirky":
            prompt = f"✨ Chaos Alert! ✨ A truly unhinged cat is {emotion} {scenario} {obstacle}. What could possibly go wrong?"
        elif style == "noir":
            prompt = f"🕵️ It was a dark night. A cat walked in, {emotion}, claiming they were {scenario}. But here's the catch—{obstacle[5:]}."
        else:
            prompt = f"A cat {emotion} {scenario} {obstacle}."

        return prompt

    def generate_batch(self, count=5):
        """Generate multiple prompts at once"""
        prompts = [self.generate_prompt() for _ in range(count)]
        return prompts


def main():
    generator = CatPromptGenerator()

    print("🎬 Funny AI Cat Video Prompt Generator 🎬\n")

    # Show available styles
    print("Available styles: standard, dramatic, quirky, noir")
    print("-" * 60)

    # Generate examples of each style
    print("\nStyle Examples:")
    for style in generator.prompt_styles:
        print(f"\n{style.upper()}:")
        print(generator.generate_prompt(style=style))

    # Interactive mode
    print("\n\n" + "=" * 60)
    print("INTERACTIVE MODE")
    print("=" * 60)
    print("Commands:")
    print("  [number] - Generate N prompts with random styles")
    print("  [style] [number] - Generate N prompts with specific style")
    print("  Available styles: standard, dramatic, quirky, noir")
    print("  'q' - Quit")
    print("-" * 60)

    while True:
        user_input = input("\n> ").strip().lower()
        if user_input == "q":
            print("\nThanks for generating cat prompts! 😸")
            break

        parts = user_input.split()

        if not parts:
            continue

        # Check if user specified a style
        style = None
        count = 5

        if len(parts) == 1:
            # Try to parse as count
            if parts[0] in generator.prompt_styles:
                style = parts[0]
            else:
                try:
                    count = int(parts[0])
                except ValueError:
                    print("Invalid input! Try '[number]' or '[style] [number]'")
                    continue
        elif len(parts) >= 2:
            # Style + count format
            if parts[0] in generator.prompt_styles:
                style = parts[0]
                try:
                    count = int(parts[1])
                except ValueError:
                    print("Invalid count! Try '[style] [number]'")
                    continue
            else:
                print(f"Unknown style '{parts[0]}'. Try: standard, dramatic, quirky, noir")
                continue

        if count <= 0:
            print("Please enter a positive number!")
            continue

        print("-" * 60)
        for i in range(1, count + 1):
            prompt = generator.generate_prompt(style=style) if style else generator.generate_prompt()
            print(f"{i}. {prompt}")



if __name__ == "__main__":
    main()
