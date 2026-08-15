import InstagramCard from "./InstagramCard.jsx";
import ESPNCard from "./ESPNCard.jsx";
import TweetCard from "./TweetCard.jsx";
import InsiderCard from "./InsiderCard.jsx";
import ArticleCard from "./ArticleCard.jsx";

export default function PostCard({ post, onChange }) {
  if (post.type === "instagram") {
    return <InstagramCard post={post} onChange={onChange} />;
  }
  if (post.type === "espn_notification") {
    return <ESPNCard post={post} onChange={onChange} />;
  }
  if (post.type === "tweet") {
    return <TweetCard post={post} onChange={onChange} />;
  }
  if (post.type === "article") {
    return <ArticleCard post={post} onChange={onChange} />;
  }
  return <InsiderCard post={post} onChange={onChange} />;
}
