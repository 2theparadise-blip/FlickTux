//! Kana → romaji → keystrokes. Sent with the IME enabled, so romaji input
//! becomes Japanese text.

use super::keys::{stroke_for_char, Stroke};

/// Katakana → Hiragana (also leaves other chars untouched).
fn to_hiragana(c: char) -> char {
    match c {
        'ァ'..='ヶ' => char::from_u32(c as u32 - 0x60).unwrap_or(c),
        _ => c,
    }
}

/// Romaji for a single kana (no digraph/sokuon handling).
fn single(c: char) -> Option<&'static str> {
    Some(match c {
        'あ' => "a", 'い' => "i", 'う' => "u", 'え' => "e", 'お' => "o",
        'ぁ' => "xa", 'ぃ' => "xi", 'ぅ' => "xu", 'ぇ' => "xe", 'ぉ' => "xo",
        'か' => "ka", 'き' => "ki", 'く' => "ku", 'け' => "ke", 'こ' => "ko",
        'が' => "ga", 'ぎ' => "gi", 'ぐ' => "gu", 'げ' => "ge", 'ご' => "go",
        'さ' => "sa", 'し' => "si", 'す' => "su", 'せ' => "se", 'そ' => "so",
        'ざ' => "za", 'じ' => "zi", 'ず' => "zu", 'ぜ' => "ze", 'ぞ' => "zo",
        'た' => "ta", 'ち' => "ti", 'つ' => "tu", 'て' => "te", 'と' => "to",
        'だ' => "da", 'ぢ' => "di", 'づ' => "du", 'で' => "de", 'ど' => "do",
        'っ' => "xtu",
        'な' => "na", 'に' => "ni", 'ぬ' => "nu", 'ね' => "ne", 'の' => "no",
        'は' => "ha", 'ひ' => "hi", 'ふ' => "hu", 'へ' => "he", 'ほ' => "ho",
        'ば' => "ba", 'び' => "bi", 'ぶ' => "bu", 'べ' => "be", 'ぼ' => "bo",
        'ぱ' => "pa", 'ぴ' => "pi", 'ぷ' => "pu", 'ぺ' => "pe", 'ぽ' => "po",
        'ま' => "ma", 'み' => "mi", 'む' => "mu", 'め' => "me", 'も' => "mo",
        'や' => "ya", 'ゆ' => "yu", 'よ' => "yo",
        'ゃ' => "xya", 'ゅ' => "xyu", 'ょ' => "xyo",
        'ら' => "ra", 'り' => "ri", 'る' => "ru", 'れ' => "re", 'ろ' => "ro",
        'わ' => "wa", 'ゐ' => "wi", 'ゑ' => "we", 'を' => "wo", 'ん' => "nn",
        'ゎ' => "xwa", 'ゔ' => "vu",
        'ー' => "-", '、' => ",", '。' => ".", '・' => "/", '「' => "[", '」' => "]",
        '！' => "!", '？' => "?", '　' => " ", '（' => "(", '）' => ")", '〜' => "~", '…' => "...",
        _ => return None,
    })
}

/// Digraphs (consonant kana + small ya/yu/yo/vowel).
fn digraph(a: char, b: char) -> Option<&'static str> {
    Some(match (a, b) {
        ('き', 'ゃ') => "kya", ('き', 'ゅ') => "kyu", ('き', 'ょ') => "kyo",
        ('ぎ', 'ゃ') => "gya", ('ぎ', 'ゅ') => "gyu", ('ぎ', 'ょ') => "gyo",
        ('し', 'ゃ') => "sya", ('し', 'ゅ') => "syu", ('し', 'ょ') => "syo",
        ('じ', 'ゃ') => "zya", ('じ', 'ゅ') => "zyu", ('じ', 'ょ') => "zyo",
        ('ち', 'ゃ') => "tya", ('ち', 'ゅ') => "tyu", ('ち', 'ょ') => "tyo",
        ('ぢ', 'ゃ') => "dya", ('ぢ', 'ゅ') => "dyu", ('ぢ', 'ょ') => "dyo",
        ('に', 'ゃ') => "nya", ('に', 'ゅ') => "nyu", ('に', 'ょ') => "nyo",
        ('ひ', 'ゃ') => "hya", ('ひ', 'ゅ') => "hyu", ('ひ', 'ょ') => "hyo",
        ('び', 'ゃ') => "bya", ('び', 'ゅ') => "byu", ('び', 'ょ') => "byo",
        ('ぴ', 'ゃ') => "pya", ('ぴ', 'ゅ') => "pyu", ('ぴ', 'ょ') => "pyo",
        ('み', 'ゃ') => "mya", ('み', 'ゅ') => "myu", ('み', 'ょ') => "myo",
        ('り', 'ゃ') => "rya", ('り', 'ゅ') => "ryu", ('り', 'ょ') => "ryo",
        ('て', 'ぃ') => "thi", ('で', 'ぃ') => "dhi",
        ('ふ', 'ぁ') => "fa", ('ふ', 'ぃ') => "fi", ('ふ', 'ぇ') => "fe", ('ふ', 'ぉ') => "fo",
        ('う', 'ぃ') => "wi", ('う', 'ぇ') => "we",
        ('ゔ', 'ぁ') => "va", ('ゔ', 'ぃ') => "vi", ('ゔ', 'ぇ') => "ve", ('ゔ', 'ぉ') => "vo",
        _ => return None,
    })
}

/// Convert kana text (hiragana/katakana, mixed with ASCII) to a romaji string.
/// Unknown characters are returned as `Err(char)`.
pub fn kana_to_romaji(text: &str) -> Result<String, char> {
    let chars: Vec<char> = text.chars().map(to_hiragana).collect();
    let mut out = String::new();
    let mut i = 0;
    let mut geminate = false; // pending っ
    while i < chars.len() {
        let c = chars[i];
        if c == 'っ' {
            geminate = true;
            i += 1;
            continue;
        }
        let (rom, used): (String, usize) = if let Some(&n) = chars.get(i + 1) {
            if let Some(r) = digraph(c, n) {
                (r.to_string(), 2)
            } else {
                (lookup(c)?, 1)
            }
        } else {
            (lookup(c)?, 1)
        };
        if geminate {
            match rom.chars().next() {
                Some(f) if f.is_ascii_alphabetic() && !"aiueon".contains(f) => out.push(f),
                _ => out.push_str("xtu"), // fall back to explicit small tsu
            }
            geminate = false;
        }
        out.push_str(&rom);
        i += used;
    }
    if geminate {
        out.push_str("xtu");
    }
    Ok(out)
}

fn lookup(c: char) -> Result<String, char> {
    if let Some(r) = single(c) {
        Ok(r.to_string())
    } else if c.is_ascii() {
        Ok(c.to_string())
    } else {
        Err(c)
    }
}

/// Convert kana text directly to keystrokes.
#[allow(dead_code)]
pub fn kana_to_strokes(text: &str) -> Result<Vec<Stroke>, char> {
    ascii_to_strokes(&kana_to_romaji(text)?)
}

/// Convert ASCII text to keystrokes.
#[allow(dead_code)]
pub fn ascii_to_strokes(text: &str) -> Result<Vec<Stroke>, char> {
    text.chars()
        .map(|c| stroke_for_char(c).ok_or(c))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn r(s: &str) -> String {
        kana_to_romaji(s).unwrap()
    }

    #[test]
    fn basic() {
        assert_eq!(r("あいうえお"), "aiueo");
        assert_eq!(r("こんにちは"), "konnnitiha");
        assert_eq!(r("かな"), "kana");
    }

    #[test]
    fn digraph_and_sokuon() {
        assert_eq!(r("しゃ"), "sya");
        assert_eq!(r("きょう"), "kyou");
        assert_eq!(r("がっこう"), "gakkou");
        assert_eq!(r("ちょっと"), "tyotto");
        assert_eq!(r("っ"), "xtu");
        assert_eq!(r("あっ"), "axtu");
    }

    #[test]
    fn katakana_and_long_vowel() {
        assert_eq!(r("コーヒー"), "ko-hi-");
        assert_eq!(r("ファイル"), "fairu");
    }

    #[test]
    fn mixed_and_symbols() {
        assert_eq!(r("abc、あ。"), "abc,a.");
    }

    #[test]
    fn unknown_char() {
        assert_eq!(kana_to_romaji("あ漢"), Err('漢'));
    }

    #[test]
    fn strokes() {
        let s = kana_to_strokes("か").unwrap();
        assert_eq!(s.len(), 2);
        assert_eq!(s[0].code, 37); // K
        assert_eq!(s[1].code, 30); // A
    }
}
