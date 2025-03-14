class FormatSpecificOptimizer:
    def __init__(self, openai_client, example_db):
        self.openai = openai_client
        self.example_db = example_db
    
    async def optimize_for_format(self, decklist, format_name):
        """Optimize a deck for a specific format using few-shot learning"""
        
        # Get successful examples for this format
        examples = await self.example_db.get_format_examples(format_name, limit=3)
        
        # Prepare few-shot examples
        few_shot_examples = []
        for example in examples:
            few_shot_examples.append({
                "original_deck": example['original_deck'],
                "optimized_deck": example['optimized_deck'],
                "optimization_rationale": example['rationale']
            })
        
        # Create prompt with few-shot examples
        prompt = self._create_few_shot_prompt(decklist, format_name, few_shot_examples)
        
        # Get optimization suggestions
        response = await self.openai.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": f"You are an expert at optimizing Magic: The Gathering decks for the {format_name} format."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        # Parse and return optimization suggestions
        return json.loads(response.choices[0].message.content)
    
    def _create_few_shot_prompt(self, decklist, format_name, examples):
        """Create a prompt with few-shot examples"""
        prompt = f"Optimize this {format_name} deck based on the current meta:\n\n"
        prompt += format_decklist(decklist)
        prompt += "\n\nHere are examples of successful optimizations for this format:\n\n"
        
        for i, example in enumerate(examples, 1):
            prompt += f"Example {i}:\n"
            prompt += f"Original deck:\n{format_decklist(example['original_deck'])}\n\n"
            prompt += f"Optimized deck:\n{format_decklist(example['optimized_deck'])}\n\n"
            prompt += f"Optimization rationale:\n{example['optimization_rationale']}\n\n"
            prompt += "-" * 40 + "\n\n"
        
        prompt += "Provide your optimization suggestions in a similar format, explaining your rationale."
        return prompt