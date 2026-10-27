
MAX_RESPONSE_WORDS = 1000

def word_count(response):
    return len(response.split())

def check_response_limit(response):
    count=word_count(response)
    if count>MAX_RESPONSE_WORDS:
        excess=count-MAX_RESPONSE_WORDS
        unit='word' if excess==1 else 'words'
        raise ValueError(f'The candidate response has {count:,} words. The limit is {MAX_RESPONSE_WORDS:,}; remove {excess:,} {unit} before assessment.')
    return count
