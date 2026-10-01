/**
 * Ghép các class name lại với nhau và loại bỏ giá trị falsy.
 * Giúp component không phải nối chuỗi thủ công khi có class có điều kiện.
 *
 * @param {...(string | false | null | undefined)} classNames
 * @returns {string}
 */
export default function cx(...classNames) {
  return classNames.filter(Boolean).join(' ')
}
